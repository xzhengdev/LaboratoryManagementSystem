import hashlib
import json
from contextlib import nullcontext
from datetime import datetime, timedelta

from flask import current_app
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import (
    Approval,
    IdempotencyRecord,
    Laboratory,
    OperationLog,
    Reservation,
)
from app.services.cache_service import (
    get_cached_lab_schedule,
    invalidate_lab_schedule_cache,
    invalidate_statistics_cache,
    set_cached_lab_schedule,
)
from app.services.distributed_lock_service import reservation_slot_lock
from app.services.event_bus_service import publish_async_event
from app.utils.exceptions import AppError
from app.utils.validators import parse_date, parse_time, require_fields

# 定义活跃预约状态常量（待审批和已批准的预约视为有效占用）
ACTIVE_RESERVATION_STATUSES = {"pending", "approved"}
IDEMPOTENCY_ENDPOINT_CREATE_RESERVATION = "create_reservation"


def write_log(user_id, module, action, detail):
    """记录操作日志的辅助函数"""
    db.session.add(
        OperationLog(user_id=user_id, module=module, action=action, detail=detail)
    )


def find_overlapping_reservation(
    lab_id, reservation_date, start_time, end_time, exclude_id=None
):
    """
    查找时间冲突的活跃预约
    参数:
        lab_id: 实验室ID
        reservation_date: 预约日期
        start_time: 开始时间
        end_time: 结束时间
        exclude_id: 排除的预约ID（用于更新场景）
    返回: 第一个冲突的预约对象，若无冲突返回None
    """
    query = Reservation.query.filter(
        Reservation.lab_id == lab_id,
        Reservation.reservation_date == reservation_date,
        Reservation.status.in_(ACTIVE_RESERVATION_STATUSES),  # 只考虑有效状态
        Reservation.start_time < end_time,  # 时间区间重叠判断
        Reservation.end_time > start_time,
    )
    if exclude_id:
        query = query.filter(Reservation.id != exclude_id)
    return query.first()


def get_lab_schedule(lab, target_date):
    """
    获取实验室某一天的完整日程安排
    返回: 包含实验室信息、日期、开放时间及所有预约的字典
    """
    cached = get_cached_lab_schedule(lab.id, target_date)
    if isinstance(cached, dict):
        return cached

    reservations = (
        Reservation.query.filter_by(lab_id=lab.id, reservation_date=target_date)
        .order_by(Reservation.start_time.asc())
        .all()
    )
    data = {
        "lab": lab.to_dict(),
        "date": target_date.isoformat(),
        "open_time": lab.open_time.strftime("%H:%M"),
        "close_time": lab.close_time.strftime("%H:%M"),
        "reservations": [item.to_dict() for item in reservations],
    }
    set_cached_lab_schedule(lab.id, target_date, data)
    return data


def _normalize_idempotency_key(idempotency_key):
    if not idempotency_key:
        return ""
    return str(idempotency_key).strip()[:128]


def _build_payload_signature(payload):
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _decode_idempotency_response(record):
    if not record.response_payload:
        return None
    try:
        value = json.loads(record.response_payload)
        if isinstance(value, dict):
            return value
    except Exception:
        return None
    return None


def _consume_existing_idempotency_record(record, request_hash):
    if record.request_hash != request_hash:
        raise AppError("同一幂等键对应的请求参数不一致，请更换 Idempotency-Key", 409, 40921)

    if record.status == "succeeded":
        cached = _decode_idempotency_response(record)
        if cached is not None:
            return None, cached
        if record.reservation_id:
            reservation = Reservation.query.get(record.reservation_id)
            if reservation:
                return None, reservation.to_dict()
        raise AppError("该请求已处理完成，请刷新后重试", 409, 40922)

    if record.status == "failed":
        raise AppError(
            record.error_message or "该请求之前已失败，请更换 Idempotency-Key 后重试",
            record.http_status or 409,
            40923,
        )

    raise AppError("请求正在处理中，请稍后重试", 409, 40924)


def _claim_idempotency_record(current_user, idempotency_key, request_hash):
    if not current_user or not idempotency_key:
        return None, None

    ttl_seconds = max(1, int(current_app.config.get("IDEMPOTENCY_TTL_SECONDS", 300)))
    now = datetime.utcnow()
    expires_at = now + timedelta(seconds=ttl_seconds)

    existing = IdempotencyRecord.query.filter_by(
        user_id=current_user.id,
        endpoint=IDEMPOTENCY_ENDPOINT_CREATE_RESERVATION,
        idempotency_key=idempotency_key,
    ).first()

    if existing and existing.expires_at <= now:
        db.session.delete(existing)
        db.session.commit()
        existing = None

    if existing:
        return _consume_existing_idempotency_record(existing, request_hash)

    record = IdempotencyRecord(
        user_id=current_user.id,
        endpoint=IDEMPOTENCY_ENDPOINT_CREATE_RESERVATION,
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        status="processing",
        expires_at=expires_at,
        http_status=202,
    )
    db.session.add(record)
    try:
        db.session.commit()
        return record, None
    except IntegrityError:
        db.session.rollback()
        existing = IdempotencyRecord.query.filter_by(
            user_id=current_user.id,
            endpoint=IDEMPOTENCY_ENDPOINT_CREATE_RESERVATION,
            idempotency_key=idempotency_key,
        ).first()
        if existing:
            return _consume_existing_idempotency_record(existing, request_hash)
        raise AppError("幂等记录创建失败，请重试", 500, 50043)


def _mark_idempotency_success(record_id, reservation_id, response_data):
    if not record_id:
        return
    try:
        record = IdempotencyRecord.query.get(record_id)
        if not record:
            return
        record.status = "succeeded"
        record.reservation_id = reservation_id
        record.http_status = 200
        record.error_message = None
        record.response_payload = json.dumps(response_data, ensure_ascii=False)
        db.session.commit()
    except Exception:
        db.session.rollback()


def _mark_idempotency_failed(record_id, error_message, http_status=400):
    if not record_id:
        return
    try:
        record = IdempotencyRecord.query.get(record_id)
        if not record:
            return
        record.status = "failed"
        record.http_status = int(http_status or 400)
        record.error_message = (error_message or "请求处理失败")[:255]
        db.session.commit()
    except Exception:
        db.session.rollback()


def create_reservation(current_user, payload, idempotency_key=None):
    """
    创建预约的核心业务逻辑
    流程: 权限校验 -> 参数校验 -> 幂等检查 -> 分布式锁 -> 冲突检测 -> 创建记录
    """
    # 必填字段校验
    require_fields(
        payload,
        ["campus_id", "lab_id", "reservation_date", "start_time", "end_time", "purpose"],
    )

    # 用户状态校验
    if current_user.status != "active":
        raise AppError("账户已被禁用，无法提交预约", 403, 40302)

    # 实验室存在性和状态校验
    lab = Laboratory.query.get(payload["lab_id"])
    if not lab:
        raise AppError("实验室不存在", 404, 40401)
    if lab.status != "active":
        raise AppError("该实验室已停用，无法预约")
    # 校区匹配校验
    if int(payload["campus_id"]) != lab.campus_id:
        raise AppError("实验室与校区不匹配")

    # 解析时间参数
    reservation_date = parse_date(payload["reservation_date"], "reservation_date")
    start_time = parse_time(payload["start_time"], "start_time")
    end_time = parse_time(payload["end_time"], "end_time")
    try:
        participant_count = int(payload.get("participant_count", 1))
    except Exception:
        raise AppError("participant_count 必须是整数")
    purpose = str(payload.get("purpose", "")).strip()
    if not purpose:
        raise AppError("预约用途不能为空")

    # 时间逻辑校验
    if start_time >= end_time:
        raise AppError("开始时间必须早于结束时间")

    now = datetime.now()
    today = now.date()
    latest_date = today + timedelta(days=7)  # 预约窗口限制为未来7天

    if reservation_date < today:
        raise AppError("不能预约过去的日期")
    if reservation_date > latest_date:
        raise AppError("预约日期不能超过未来7天")

    start_at = datetime.combine(reservation_date, start_time)
    end_at = datetime.combine(reservation_date, end_time)

    # 当天预约的特殊校验：不能预约已经过去的时间段
    if reservation_date == today and end_at <= now:
        raise AppError("不能预约今天已过去的时间段")

    # 提前30分钟预约限制
    if start_at < now + timedelta(minutes=30):
        raise AppError("预约开始时间必须至少提前30分钟")

    # 实验室开放时间范围校验
    if start_time < lab.open_time or end_time > lab.close_time:
        raise AppError("预约时间必须在实验室开放时间范围内")

    # 容量校验
    if participant_count <= 0:
        raise AppError("参与人数必须大于 0")
    if participant_count > lab.capacity:
        raise AppError("参与人数超过实验室容量上限")

    # 幂等处理（可选）
    idempotency_record = None
    normalized_idempotency_key = _normalize_idempotency_key(idempotency_key)
    if current_app.config.get("ENABLE_IDEMPOTENCY", True) and normalized_idempotency_key:
        request_hash = _build_payload_signature(
            {
                "user_id": current_user.id,
                "campus_id": int(payload["campus_id"]),
                "lab_id": int(payload["lab_id"]),
                "reservation_date": reservation_date.isoformat(),
                "start_time": start_time.strftime("%H:%M:%S"),
                "end_time": end_time.strftime("%H:%M:%S"),
                "purpose": purpose,
                "participant_count": participant_count,
            }
        )
        idempotency_record, cached_result = _claim_idempotency_record(
            current_user, normalized_idempotency_key, request_hash
        )
        if cached_result is not None:
            return cached_result

    try:
        # 关键路径加锁：同实验室同日期串行，避免并发创建时冲突漏检。
        with reservation_slot_lock(lab.id, reservation_date):
            # 时间冲突检测
            overlapping = find_overlapping_reservation(
                lab.id, reservation_date, start_time, end_time
            )
            if overlapping:
                raise AppError("当前时间段已被占用，请选择其他时间")

            # 根据用户角色决定是否需要审批（学生和教师需要审批，管理员直接通过）
            need_approval = current_user.role in {"student", "teacher"}
            status = "pending" if need_approval else "approved"

            # 创建预约记录
            reservation = Reservation(
                user_id=current_user.id,
                campus_id=lab.campus_id,
                lab_id=lab.id,
                reservation_date=reservation_date,
                start_time=start_time,
                end_time=end_time,
                purpose=purpose,
                participant_count=participant_count,
                status=status,
                need_approval=need_approval,
            )
            db.session.add(reservation)
            db.session.flush()  # 获取自增ID

            # 管理员自动通过时，直接创建审批记录
            if not need_approval:
                db.session.add(
                    Approval(
                        reservation_id=reservation.id,
                        approver_id=current_user.id,
                        approval_status="approved",
                        remark="管理员自助预约自动通过",
                        approval_time=datetime.utcnow(),
                    )
                )

            # 记录操作日志
            write_log(
                current_user.id,
                "reservation",
                "create",
                f"创建预约 #{reservation.id}，实验室 {lab.lab_name}，日期 {reservation_date.isoformat()}",
            )
            db.session.commit()
            invalidate_lab_schedule_cache(lab.id, reservation_date)
            invalidate_statistics_cache()
            result = reservation.to_dict()
            publish_async_event(
                "reservation.created",
                {
                    "reservation_id": reservation.id,
                    "user_id": current_user.id,
                    "campus_id": reservation.campus_id,
                    "lab_id": reservation.lab_id,
                    "reservation_date": reservation.reservation_date.isoformat(),
                    "start_time": reservation.start_time.strftime("%H:%M:%S"),
                    "end_time": reservation.end_time.strftime("%H:%M:%S"),
                    "status": reservation.status,
                },
            )

        if idempotency_record:
            _mark_idempotency_success(idempotency_record.id, reservation.id, result)
        return result

    except AppError as error:
        db.session.rollback()
        if idempotency_record:
            _mark_idempotency_failed(idempotency_record.id, error.message, error.code)
        raise
    except Exception:
        db.session.rollback()
        if idempotency_record:
            _mark_idempotency_failed(idempotency_record.id, "服务器内部错误", 500)
        raise


def cancel_reservation(current_user, reservation):
    """
    取消预约
    权限规则:
        - 学生/教师: 只能取消自己的预约
        - 实验室管理员: 只能取消本校区的预约
        - 系统管理员: 可以取消任何预约
    """
    # 状态校验：已取消或已拒绝的预约不可再取消
    if reservation.status in {"cancelled", "rejected"}:
        raise AppError("当前预约状态不允许取消")

    # 权限校验：非管理员只能取消自己的
    if (
        current_user.role not in {"lab_admin", "system_admin"}
        and reservation.user_id != current_user.id
    ):
        raise AppError("只能取消自己的预约", 403, 40303)

    # 实验室管理员跨校区限制
    if (
        current_user.role == "lab_admin"
        and current_user.campus_id != reservation.campus_id
    ):
        raise AppError("只能取消本校区的预约", 403, 40304)

    reservation.status = "cancelled"
    write_log(current_user.id, "reservation", "cancel", f"取消预约 #{reservation.id}")
    db.session.commit()
    invalidate_lab_schedule_cache(reservation.lab_id, reservation.reservation_date)
    invalidate_statistics_cache()
    publish_async_event(
        "reservation.cancelled",
        {
            "reservation_id": reservation.id,
            "user_id": current_user.id,
            "campus_id": reservation.campus_id,
            "lab_id": reservation.lab_id,
            "reservation_date": reservation.reservation_date.isoformat(),
            "status": reservation.status,
        },
    )
    return reservation.to_dict()


def list_reservations(current_user, filters):
    """
    预约列表查询（带角色权限过滤）
    - 学生/教师: 只看到自己的预约
    - 实验室管理员: 看到本校区的所有预约
    - 系统管理员: 看到所有预约
    """
    query = Reservation.query.order_by(Reservation.created_at.desc())

    # 角色权限过滤
    if current_user.role in {"student", "teacher"}:
        query = query.filter_by(user_id=current_user.id)
    elif current_user.role == "lab_admin":
        query = query.filter_by(campus_id=current_user.campus_id)

    # 可选筛选条件
    if filters.get("status"):
        query = query.filter_by(status=filters["status"])
    if filters.get("campus_id"):
        query = query.filter_by(campus_id=int(filters["campus_id"]))
    if filters.get("lab_id"):
        query = query.filter_by(lab_id=int(filters["lab_id"]))

    return [item.to_dict() for item in query.all()]


def approve_reservation(current_user, reservation, approval_status, remark):
    """
    审批预约
    流程: 权限校验 -> 状态校验 -> (如果通过)加锁冲突检测 -> 更新状态并记录审批
    """
    # 管理员权限校验
    if current_user.role not in {"lab_admin", "system_admin"}:
        raise AppError("只有管理员可以审批预约", 403, 40305)

    # 实验室管理员校区限制
    if (
        current_user.role == "lab_admin"
        and current_user.campus_id != reservation.campus_id
    ):
        raise AppError("只能审批本校区预约", 403, 40306)

    # 状态校验：只有待审批的预约才能被审批
    if reservation.status != "pending":
        raise AppError("当前预约不在待审批状态")

    # 审批结果值校验
    if approval_status not in {"approved", "rejected"}:
        raise AppError("审批状态只能是 approved 或 rejected")

    lock_context = (
        reservation_slot_lock(reservation.lab_id, reservation.reservation_date)
        if approval_status == "approved"
        else nullcontext()
    )

    try:
        with lock_context:
            # 批准通过时，重新检查时间冲突（防止等待审批期间被其他预约占用）
            if approval_status == "approved":
                overlapping = find_overlapping_reservation(
                    reservation.lab_id,
                    reservation.reservation_date,
                    reservation.start_time,
                    reservation.end_time,
                    exclude_id=reservation.id,  # 排除自身
                )
                if overlapping:
                    raise AppError("审批失败，该时间段已有其他有效预约")

            # 更新预约状态
            reservation.status = approval_status

            # 创建审批记录
            approval = Approval(
                reservation_id=reservation.id,
                approver_id=current_user.id,
                approval_status=approval_status,
                remark=remark or "",
                approval_time=datetime.utcnow(),
            )
            db.session.add(approval)

            # 记录日志
            write_log(
                current_user.id,
                "approval",
                approval_status,
                f"审批预约 #{reservation.id}，结果 {approval_status}",
            )
            db.session.commit()
            invalidate_lab_schedule_cache(reservation.lab_id, reservation.reservation_date)
            invalidate_statistics_cache()
            publish_async_event(
                f"reservation.{approval_status}",
                {
                    "reservation_id": reservation.id,
                    "user_id": current_user.id,
                    "campus_id": reservation.campus_id,
                    "lab_id": reservation.lab_id,
                    "reservation_date": reservation.reservation_date.isoformat(),
                    "status": reservation.status,
                    "approval_id": approval.id,
                },
            )

        # 返回预约信息，附带审批记录
        return reservation.to_dict({"approval": approval.to_dict()})
    except Exception:
        db.session.rollback()
        raise

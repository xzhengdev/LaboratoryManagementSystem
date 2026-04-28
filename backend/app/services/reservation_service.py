import hashlib
import json
from contextlib import nullcontext
from datetime import datetime, timedelta

from flask import current_app
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Approval, IdempotencyRecord, Laboratory, OperationLog, Reservation
from app.services.cache_service import (
    get_cached_lab_schedule,
    invalidate_lab_schedule_cache,
    invalidate_statistics_cache,
    set_cached_lab_schedule,
)
from app.services.db_router_service import campus_db_session, get_routed_campus_ids
from app.services.distributed_lock_service import reservation_slot_lock
from app.services.event_bus_service import publish_async_event
from app.utils.exceptions import AppError
from app.utils.validators import parse_date, parse_time, require_fields

ACTIVE_RESERVATION_STATUSES = {"pending", "approved"}
IDEMPOTENCY_ENDPOINT_CREATE_RESERVATION = "create_reservation"


def _campus_candidates_for_user(current_user):
    if current_user.role == "system_admin":
        campus_ids = get_routed_campus_ids()
        return campus_ids or [0]
    return [current_user.campus_id or 0]


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


def _mark_idempotency_success(record_id, response_data):
    if not record_id:
        return
    try:
        record = IdempotencyRecord.query.get(record_id)
        if not record:
            return
        record.status = "succeeded"
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


def _write_log(session, user_id, module, action, detail):
    session.add(OperationLog(user_id=user_id, module=module, action=action, detail=detail))


def _find_overlapping_reservation(session, lab_id, reservation_date, start_time, end_time, exclude_id=None):
    query = session.query(Reservation).filter(
        Reservation.lab_id == lab_id,
        Reservation.reservation_date == reservation_date,
        Reservation.status.in_(ACTIVE_RESERVATION_STATUSES),
        Reservation.start_time < end_time,
        Reservation.end_time > start_time,
    )
    if exclude_id:
        query = query.filter(Reservation.id != exclude_id)
    return query.first()


def _get_lab_by_campus(session, campus_id, lab_id):
    lab = session.query(Laboratory).get(int(lab_id))
    if not lab:
        raise AppError("实验室不存在", 404, 40401)
    if int(campus_id) != lab.campus_id:
        raise AppError("实验室与校区不匹配")
    return lab


def _resolve_reservation(current_user, reservation_id):
    for campus_id in _campus_candidates_for_user(current_user):
        with campus_db_session(campus_id) as session:
            item = session.query(Reservation).get(int(reservation_id))
            if item:
                return item.to_dict(), campus_id
    raise AppError("预约不存在", 404, 40421)


def _get_reservation_from_campus(session, reservation_id):
    item = session.query(Reservation).get(int(reservation_id))
    if not item:
        raise AppError("预约不存在", 404, 40421)
    return item


def get_lab_schedule(lab, target_date):
    cached = get_cached_lab_schedule(lab.id, target_date, campus_id=lab.campus_id)
    if isinstance(cached, dict):
        return cached

    with campus_db_session(lab.campus_id) as session:
        reservations = (
            session.query(Reservation)
            .filter_by(lab_id=lab.id, reservation_date=target_date)
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
    set_cached_lab_schedule(lab.id, target_date, data, campus_id=lab.campus_id)
    return data


def create_reservation(current_user, payload, idempotency_key=None):
    require_fields(
        payload,
        ["campus_id", "lab_id", "reservation_date", "start_time", "end_time", "purpose"],
    )

    if current_user.status != "active":
        raise AppError("账户已被禁用，无法提交预约", 403, 40302)

    campus_id = int(payload["campus_id"])
    if current_user.role == "lab_admin" and current_user.campus_id != campus_id:
        raise AppError("只能操作本校区预约", 403, 40358)
    if current_user.role in {"student", "teacher"} and current_user.campus_id != campus_id:
        raise AppError("只能提交本校区预约", 403, 40359)

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

    if start_time >= end_time:
        raise AppError("开始时间必须早于结束时间")

    now = datetime.now()
    today = now.date()
    latest_date = today + timedelta(days=7)

    if reservation_date < today:
        raise AppError("不能预约过去的日期")
    if reservation_date > latest_date:
        raise AppError("预约日期不能超过未来7天")

    start_at = datetime.combine(reservation_date, start_time)
    end_at = datetime.combine(reservation_date, end_time)

    if reservation_date == today and end_at <= now:
        raise AppError("不能预约今天已过去的时间段")

    if start_at < now + timedelta(minutes=30):
        raise AppError("预约开始时间必须至少提前30分钟")

    if participant_count <= 0:
        raise AppError("参与人数必须大于 0")

    idempotency_record = None
    normalized_idempotency_key = _normalize_idempotency_key(idempotency_key)
    if current_app.config.get("ENABLE_IDEMPOTENCY", True) and normalized_idempotency_key:
        request_hash = _build_payload_signature(
            {
                "user_id": current_user.id,
                "campus_id": campus_id,
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

    with campus_db_session(campus_id) as session:
        try:
            lab = _get_lab_by_campus(session, campus_id, payload["lab_id"])

            if start_time < lab.open_time or end_time > lab.close_time:
                raise AppError("预约时间必须在实验室开放时间范围内")
            if participant_count > lab.capacity:
                raise AppError("参与人数超过实验室容量上限")

            with reservation_slot_lock(lab.id, reservation_date):
                overlapping = _find_overlapping_reservation(
                    session, lab.id, reservation_date, start_time, end_time
                )
                if overlapping:
                    raise AppError("当前时间段已被占用，请选择其他时间")

                need_approval = current_user.role in {"student", "teacher"}
                status = "pending" if need_approval else "approved"

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
                session.add(reservation)
                session.flush()

                if not need_approval:
                    session.add(
                        Approval(
                            reservation_id=reservation.id,
                            approver_id=current_user.id,
                            approval_status="approved",
                            remark="管理员自助预约自动通过",
                            approval_time=datetime.utcnow(),
                        )
                    )

                _write_log(
                    session,
                    current_user.id,
                    "reservation",
                    "create",
                    f"创建预约 #{reservation.id}，实验室 {lab.lab_name}，日期 {reservation_date.isoformat()}",
                )
                session.commit()
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

            invalidate_lab_schedule_cache(lab.id, reservation_date, campus_id=lab.campus_id)
            invalidate_statistics_cache()
            if idempotency_record:
                _mark_idempotency_success(idempotency_record.id, result)
            return result
        except AppError as error:
            session.rollback()
            if idempotency_record:
                _mark_idempotency_failed(idempotency_record.id, error.message, error.code)
            raise
        except Exception:
            session.rollback()
            if idempotency_record:
                _mark_idempotency_failed(idempotency_record.id, "服务器内部错误", 500)
            raise


def get_reservation_detail(current_user, reservation_id):
    snapshot, campus_id = _resolve_reservation(current_user, reservation_id)
    with campus_db_session(campus_id) as session:
        item = _get_reservation_from_campus(session, reservation_id)

        if current_user.role in {"student", "teacher"} and item.user_id != current_user.id:
            raise AppError("只能查看自己的预约", 403, 40317)
        if current_user.role == "lab_admin" and current_user.campus_id != item.campus_id:
            raise AppError("只能查看本校区预约", 403, 40318)

        return item.to_dict({"approvals": [approval.to_dict() for approval in item.approvals]})


def cancel_reservation(current_user, reservation):
    # 兼容旧调用，内部走按 id 取消。
    return cancel_reservation_by_id(current_user, reservation.id)


def cancel_reservation_by_id(current_user, reservation_id):
    snapshot, campus_id = _resolve_reservation(current_user, reservation_id)
    with campus_db_session(campus_id) as session:
        item = _get_reservation_from_campus(session, reservation_id)

        if item.status in {"cancelled", "rejected"}:
            raise AppError("当前预约状态不允许取消")

        if current_user.role not in {"lab_admin", "system_admin"} and item.user_id != current_user.id:
            raise AppError("只能取消自己的预约", 403, 40303)

        if current_user.role == "lab_admin" and current_user.campus_id != item.campus_id:
            raise AppError("只能取消本校区的预约", 403, 40304)

        item.status = "cancelled"
        _write_log(session, current_user.id, "reservation", "cancel", f"取消预约 #{item.id}")
        session.commit()
        result = item.to_dict()

    invalidate_lab_schedule_cache(result["lab_id"], result["reservation_date"], campus_id=result["campus_id"])
    invalidate_statistics_cache()
    publish_async_event(
        "reservation.cancelled",
        {
            "reservation_id": result["id"],
            "user_id": current_user.id,
            "campus_id": result["campus_id"],
            "lab_id": result["lab_id"],
            "reservation_date": result["reservation_date"],
            "status": result["status"],
        },
    )
    return result


def delete_reservation_by_id(current_user, reservation_id):
    snapshot, campus_id = _resolve_reservation(current_user, reservation_id)
    with campus_db_session(campus_id) as session:
        item = _get_reservation_from_campus(session, reservation_id)
        if item.user_id != current_user.id:
            raise AppError("只能删除自己的预约", 403, 40331)
        if item.status not in {"rejected", "cancelled"}:
            raise AppError("仅已拒绝或已取消的预约可删除", 400, 40071)

        session.query(Approval).filter_by(reservation_id=item.id).delete(synchronize_session=False)
        session.delete(item)
        session.commit()
    invalidate_statistics_cache()
    return True


def _list_reservations_in_session(session, current_user, filters):
    query = session.query(Reservation).order_by(Reservation.created_at.desc())

    if current_user.role in {"student", "teacher"}:
        query = query.filter_by(user_id=current_user.id)
    elif current_user.role == "lab_admin":
        query = query.filter_by(campus_id=current_user.campus_id)

    if filters.get("status"):
        query = query.filter_by(status=str(filters["status"]))
    if filters.get("campus_id") and current_user.role == "system_admin":
        query = query.filter_by(campus_id=int(filters["campus_id"]))
    if filters.get("lab_id"):
        query = query.filter_by(lab_id=int(filters["lab_id"]))

    return [item.to_dict() for item in query.all()]


def list_reservations(current_user, filters):
    if filters.get("campus_id"):
        target_campus_id = int(filters["campus_id"])
        if current_user.role == "lab_admin" and target_campus_id != current_user.campus_id:
            raise AppError("只能查看本校区预约", 403, 40360)
        with campus_db_session(target_campus_id) as session:
            return _list_reservations_in_session(session, current_user, filters)

    if current_user.role == "system_admin":
        campus_ids = get_routed_campus_ids()
        if not campus_ids:
            with campus_db_session(0) as session:
                return _list_reservations_in_session(session, current_user, filters)
        rows = []
        for campus_id in campus_ids:
            with campus_db_session(campus_id) as session:
                rows.extend(_list_reservations_in_session(session, current_user, filters))
        rows.sort(key=lambda item: item.get("created_at") or "", reverse=True)
        return rows

    with campus_db_session(current_user.campus_id) as session:
        return _list_reservations_in_session(session, current_user, filters)


def list_pending_approvals(current_user):
    if current_user.role not in {"lab_admin", "system_admin"}:
        raise AppError("只有管理员可以查看待审批列表", 403, 40305)

    def _query_pending(session):
        query = session.query(Reservation).filter_by(status="pending").order_by(Reservation.created_at.desc())
        if current_user.role == "lab_admin":
            query = query.filter_by(campus_id=current_user.campus_id)
        return [item.to_dict() for item in query.all()]

    if current_user.role == "system_admin":
        campus_ids = get_routed_campus_ids()
        if not campus_ids:
            with campus_db_session(0) as session:
                return _query_pending(session)
        rows = []
        for campus_id in campus_ids:
            with campus_db_session(campus_id) as session:
                rows.extend(_query_pending(session))
        rows.sort(key=lambda item: item.get("created_at") or "", reverse=True)
        return rows

    with campus_db_session(current_user.campus_id) as session:
        return _query_pending(session)


def approve_reservation(current_user, reservation, approval_status, remark):
    # 兼容旧调用
    return approve_reservation_by_id(current_user, reservation.id, approval_status, remark)


def approve_reservation_by_id(current_user, reservation_id, approval_status, remark):
    if current_user.role not in {"lab_admin", "system_admin"}:
        raise AppError("只有管理员可以审批预约", 403, 40305)

    _, campus_id = _resolve_reservation(current_user, reservation_id)
    with campus_db_session(campus_id) as session:
        reservation = _get_reservation_from_campus(session, reservation_id)

        if current_user.role == "lab_admin" and current_user.campus_id != reservation.campus_id:
            raise AppError("只能审批本校区预约", 403, 40306)

        if reservation.status != "pending":
            raise AppError("当前预约不在待审批状态")

        if approval_status not in {"approved", "rejected"}:
            raise AppError("审批状态只能是 approved 或 rejected")

        lock_context = (
            reservation_slot_lock(reservation.lab_id, reservation.reservation_date)
            if approval_status == "approved"
            else nullcontext()
        )

        try:
            with lock_context:
                if approval_status == "approved":
                    overlapping = _find_overlapping_reservation(
                        session,
                        reservation.lab_id,
                        reservation.reservation_date,
                        reservation.start_time,
                        reservation.end_time,
                        exclude_id=reservation.id,
                    )
                    if overlapping:
                        raise AppError("审批失败，该时间段已有其他有效预约")

                reservation.status = approval_status

                approval = Approval(
                    reservation_id=reservation.id,
                    approver_id=current_user.id,
                    approval_status=approval_status,
                    remark=remark or "",
                    approval_time=datetime.utcnow(),
                )
                session.add(approval)

                _write_log(
                    session,
                    current_user.id,
                    "approval",
                    approval_status,
                    f"审批预约 #{reservation.id}，结果 {approval_status}",
                )
                session.commit()
                result = reservation.to_dict({"approval": approval.to_dict()})

            invalidate_lab_schedule_cache(
                reservation.lab_id,
                reservation.reservation_date,
                campus_id=reservation.campus_id,
            )
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
            return result
        except Exception:
            session.rollback()
            raise

from datetime import datetime

from app.extensions import db
from app.models import Approval, Laboratory, OperationLog, Reservation
from app.utils.exceptions import AppError
from app.utils.validators import parse_date, parse_time, require_fields


ACTIVE_RESERVATION_STATUSES = {"pending", "approved"}


def write_log(user_id, module, action, detail):
    # 统一写入操作日志，避免在各个业务函数里重复写 db.session.add。
    db.session.add(
        OperationLog(user_id=user_id, module=module, action=action, detail=detail)
    )


def find_overlapping_reservation(
    lab_id, reservation_date, start_time, end_time, exclude_id=None
):
    # 判断时间段是否冲突：
    # start < 已有 end 且 end > 已有 start 时视为重叠。
    query = Reservation.query.filter(
        Reservation.lab_id == lab_id,
        Reservation.reservation_date == reservation_date,
        Reservation.status.in_(ACTIVE_RESERVATION_STATUSES),
        Reservation.start_time < end_time,
        Reservation.end_time > start_time,
    )
    if exclude_id:
        query = query.filter(Reservation.id != exclude_id)
    return query.first()


def get_lab_schedule(lab, target_date):
    # 查询某实验室某一天的所有预约记录，供详情页/排期页/Agent 使用。
    reservations = (
        Reservation.query.filter_by(lab_id=lab.id, reservation_date=target_date)
        .order_by(Reservation.start_time.asc())
        .all()
    )
    return {
        "lab": lab.to_dict(),
        "date": target_date.isoformat(),
        "open_time": lab.open_time.strftime("%H:%M"),
        "close_time": lab.close_time.strftime("%H:%M"),
        "reservations": [item.to_dict() for item in reservations],
    }


def create_reservation(current_user, payload):
    # 创建预约的核心业务规则都集中在这里，确保前后端规则统一。
    require_fields(
        payload,
        ["campus_id", "lab_id", "reservation_date", "start_time", "end_time", "purpose"],
    )

    if current_user.status != "active":
        raise AppError("账户已被禁用，无法提交预约", 403, 40302)

    # 实验室必须存在且必须与传入校区匹配。
    lab = Laboratory.query.get(payload["lab_id"])
    if not lab:
        raise AppError("实验室不存在", 404, 40401)
    if lab.status != "active":
        raise AppError("该实验室已停用，无法预约")
    if int(payload["campus_id"]) != lab.campus_id:
        raise AppError("实验室与校区不匹配")

    reservation_date = parse_date(payload["reservation_date"], "reservation_date")
    start_time = parse_time(payload["start_time"], "start_time")
    end_time = parse_time(payload["end_time"], "end_time")
    participant_count = int(payload.get("participant_count", 1))

    # 依次校验时间顺序、开放时间范围、人数上限。
    if start_time >= end_time:
        raise AppError("开始时间必须早于结束时间")
    if start_time < lab.open_time or end_time > lab.close_time:
        raise AppError("预约时间必须在实验室开放时间范围内")
    if participant_count > lab.capacity:
        raise AppError("参与人数超过实验室容量上限")

    # 检查是否与其他有效预约冲突。
    overlapping = find_overlapping_reservation(
        lab.id, reservation_date, start_time, end_time
    )
    if overlapping:
        raise AppError("当前时间段已被占用，请选择其他时间")

    # 普通用户提交预约需要走审批，管理员可直接通过。
    need_approval = current_user.role in {"student", "teacher"}
    status = "pending" if need_approval else "approved"

    reservation = Reservation(
        user_id=current_user.id,
        campus_id=lab.campus_id,
        lab_id=lab.id,
        reservation_date=reservation_date,
        start_time=start_time,
        end_time=end_time,
        purpose=payload["purpose"],
        participant_count=participant_count,
        status=status,
        need_approval=need_approval,
    )
    db.session.add(reservation)
    db.session.flush()

    # 管理员自助预约时自动写入一条已通过审批记录。
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

    # 写操作日志后再提交事务。
    write_log(
        current_user.id,
        "reservation",
        "create",
        f"创建预约 #{reservation.id}，实验室 {lab.lab_name}，日期 {reservation_date.isoformat()}",
    )
    db.session.commit()
    return reservation.to_dict()


def cancel_reservation(current_user, reservation):
    # 取消预约时校验：
    # 1. 当前状态是否允许取消
    # 2. 当前用户是否有权限取消这条预约
    if reservation.status in {"cancelled", "rejected"}:
        raise AppError("当前预约状态不允许取消")
    if current_user.role not in {"lab_admin", "system_admin"} and reservation.user_id != current_user.id:
        raise AppError("只能取消自己的预约", 403, 40303)
    if current_user.role == "lab_admin" and current_user.campus_id != reservation.campus_id:
        raise AppError("只能取消本校区的预约", 403, 40304)

    reservation.status = "cancelled"
    write_log(current_user.id, "reservation", "cancel", f"取消预约 #{reservation.id}")
    db.session.commit()
    return reservation.to_dict()


def list_reservations(current_user, filters):
    # 预约列表权限规则：
    # 学生/教师只能看自己的；
    # 实验室管理员只能看自己校区；
    # 系统管理员可以看全部。
    query = Reservation.query.order_by(Reservation.created_at.desc())
    if current_user.role in {"student", "teacher"}:
        query = query.filter_by(user_id=current_user.id)
    elif current_user.role == "lab_admin":
        query = query.filter_by(campus_id=current_user.campus_id)

    # 再按状态、校区、实验室做二次过滤。
    if filters.get("status"):
        query = query.filter_by(status=filters["status"])
    if filters.get("campus_id"):
        query = query.filter_by(campus_id=int(filters["campus_id"]))
    if filters.get("lab_id"):
        query = query.filter_by(lab_id=int(filters["lab_id"]))

    return [item.to_dict() for item in query.all()]


def approve_reservation(current_user, reservation, approval_status, remark):
    # 审批逻辑集中在 service 层，确保 API 层只负责收参和返回。
    if current_user.role not in {"lab_admin", "system_admin"}:
        raise AppError("只有管理员可以审批预约", 403, 40305)
    if current_user.role == "lab_admin" and current_user.campus_id != reservation.campus_id:
        raise AppError("只能审批本校区预约", 403, 40306)
    if reservation.status != "pending":
        raise AppError("当前预约不在待审批状态")
    if approval_status not in {"approved", "rejected"}:
        raise AppError("审批状态只能是 approved 或 rejected")

    # 审批通过前再次校验是否与其他有效预约冲突，
    # 避免多个管理员同时处理时产生并发穿透。
    if approval_status == "approved":
        overlapping = find_overlapping_reservation(
            reservation.lab_id,
            reservation.reservation_date,
            reservation.start_time,
            reservation.end_time,
            exclude_id=reservation.id,
        )
        if overlapping:
            raise AppError("审批失败，该时间段已有其他有效预约")

    # 写审批记录并同步主预约状态。
    reservation.status = approval_status
    approval = Approval(
        reservation_id=reservation.id,
        approver_id=current_user.id,
        approval_status=approval_status,
        remark=remark or "",
        approval_time=datetime.utcnow(),
    )
    db.session.add(approval)
    write_log(
        current_user.id,
        "approval",
        approval_status,
        f"审批预约 #{reservation.id}，结果 {approval_status}",
    )
    db.session.commit()
    return reservation.to_dict({"approval": approval.to_dict()})

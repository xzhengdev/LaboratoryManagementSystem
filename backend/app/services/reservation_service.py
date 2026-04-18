from datetime import datetime, timedelta

from app.extensions import db
from app.models import Approval, Laboratory, OperationLog, Reservation
from app.utils.exceptions import AppError
from app.utils.validators import parse_date, parse_time, require_fields

# 定义活跃预约状态常量（待审批和已批准的预约视为有效占用）
ACTIVE_RESERVATION_STATUSES = {"pending", "approved"}


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
    """
    创建预约的核心业务逻辑
    流程: 权限校验 -> 参数校验 -> 时间合法性 -> 冲突检测 -> 创建记录
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
    participant_count = int(payload.get("participant_count", 1))

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
    if participant_count > lab.capacity:
        raise AppError("参与人数超过实验室容量上限")

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
        purpose=payload["purpose"],
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
    return reservation.to_dict()


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
    if current_user.role not in {"lab_admin", "system_admin"} and reservation.user_id != current_user.id:
        raise AppError("只能取消自己的预约", 403, 40303)
    
    # 实验室管理员跨校区限制
    if current_user.role == "lab_admin" and current_user.campus_id != reservation.campus_id:
        raise AppError("只能取消本校区的预约", 403, 40304)

    reservation.status = "cancelled"
    write_log(current_user.id, "reservation", "cancel", f"取消预约 #{reservation.id}")
    db.session.commit()
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
    流程: 权限校验 -> 状态校验 -> (如果通过)冲突检测 -> 更新状态并记录审批
    """
    # 管理员权限校验
    if current_user.role not in {"lab_admin", "system_admin"}:
        raise AppError("只有管理员可以审批预约", 403, 40305)
    
    # 实验室管理员校区限制
    if current_user.role == "lab_admin" and current_user.campus_id != reservation.campus_id:
        raise AppError("只能审批本校区预约", 403, 40306)
    
    # 状态校验：只有待审批的预约才能被审批
    if reservation.status != "pending":
        raise AppError("当前预约不在待审批状态")
    
    # 审批结果值校验
    if approval_status not in {"approved", "rejected"}:
        raise AppError("审批状态只能是 approved 或 rejected")

    # 批准通过时，需要重新检查时间冲突（防止在等待审批期间被其他预约占用）
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
    
    # 返回预约信息，附带审批记录
    return reservation.to_dict({"approval": approval.to_dict()})
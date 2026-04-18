"""
预约服务模块 (reservation_service.py)
功能：预约的核心业务逻辑，包括创建、取消、查询、审批等
      所有预约相关的规则都集中在此，确保前后端规则统一
"""

from datetime import datetime  # 日期时间处理

from app.extensions import db  # 数据库实例
from app.models import Approval, Laboratory, OperationLog, Reservation  # 数据模型
from app.utils.exceptions import AppError  # 自定义异常类
from app.utils.validators import parse_date, parse_time, require_fields  # 参数验证

# ==================== 常量定义 ====================
# 活跃的预约状态（这些状态的预约会占用实验室时间段）
ACTIVE_RESERVATION_STATUSES = {"pending", "approved"}


# ==================== 操作日志 ====================
def write_log(user_id, module, action, detail):
    """
    统一写入操作日志
    
    功能：记录用户的关键操作（创建预约、取消预约、审批等）
    目的：避免在各个业务函数中重复写 db.session.add
    
    参数：
        user_id - 操作用户ID
        module  - 模块名称（如 reservation, approval）
        action  - 操作类型（如 create, cancel, approved）
        detail  - 操作详情描述
    """
    db.session.add(
        OperationLog(user_id=user_id, module=module, action=action, detail=detail)
    )


# ==================== 时间冲突检测 ====================
def find_overlapping_reservation(
    lab_id, reservation_date, start_time, end_time, exclude_id=None
):
    """
    查找与指定时间段冲突的预约
    
    冲突判断逻辑：
        新预约开始时间 < 已有预约结束时间 
        AND 
        新预约结束时间 > 已有预约开始时间
        = 有时间重叠
    
    参数：
        lab_id          - 实验室ID
        reservation_date - 预约日期
        start_time      - 开始时间
        end_time        - 结束时间
        exclude_id      - 排除的预约ID（用于更新时排除自身）
    
    返回：
        第一个冲突的预约对象，无冲突返回 None
    """
    # 查询条件：
    # 1. 同一实验室
    # 2. 同一日期
    # 3. 状态为活跃（pending 或 approved）
    # 4. 时间重叠：start < 已有.end AND end > 已有.start
    query = Reservation.query.filter(
        Reservation.lab_id == lab_id,
        Reservation.reservation_date == reservation_date,
        Reservation.status.in_(ACTIVE_RESERVATION_STATUSES),
        Reservation.start_time < end_time,      # 新开始 < 旧结束
        Reservation.end_time > start_time,      # 新结束 > 旧开始
    )
    
    # 更新时排除自己
    if exclude_id:
        query = query.filter(Reservation.id != exclude_id)
    
    return query.first()


# ==================== 实验室排期查询 ====================
def get_lab_schedule(lab, target_date):
    """
    查询实验室某一天的完整排期
    
    功能：返回实验室信息、开放时间、以及当天的所有预约
    
    参数：
        lab         - 实验室对象
        target_date - 目标日期（date 对象）
    
    返回：
        {
            "lab": {...},                    # 实验室信息
            "date": "2024-01-15",           # 日期
            "open_time": "09:00",           # 开放时间
            "close_time": "21:00",          # 关闭时间
            "reservations": [...]           # 当天所有预约列表
        }
    """
    # 查询当天所有预约，按开始时间升序排列
    reservations = (
        Reservation.query.filter_by(lab_id=lab.id, reservation_date=target_date)
        .order_by(Reservation.start_time.asc())
        .all()
    )
    
    return {
        "lab": lab.to_dict(),
        "date": target_date.isoformat(),
        "open_time": lab.open_time.strftime("%H:%M"),   # 时间格式化
        "close_time": lab.close_time.strftime("%H:%M"),
        "reservations": [item.to_dict() for item in reservations],
    }


# ==================== 创建预约 ====================
def create_reservation(current_user, payload):
    """
    创建预约的核心业务逻辑
    
    参数：
        current_user - 当前登录用户
        payload      - 请求数据（包含预约信息）
    
    返回：
        创建成功的预约对象字典
    
    异常：
        AppError - 各种校验失败时抛出
    
    校验规则：
        1. 账户状态检查
        2. 实验室存在且活跃
        3. 实验室与校区匹配
        4. 时间顺序正确
        5. 时间在开放范围内
        6. 人数未超容量
        7. 时间不冲突
    """
    # ----- 1. 参数验证 -----
    require_fields(
        payload,
        ["campus_id", "lab_id", "reservation_date", "start_time", "end_time", "purpose"],
    )

    # ----- 2. 账户状态检查 -----
    if current_user.status != "active":
        raise AppError("账户已被禁用，无法提交预约", 403, 40302)

    # ----- 3. 实验室存在且活跃 -----
    lab = Laboratory.query.get(payload["lab_id"])
    if not lab:
        raise AppError("实验室不存在", 404, 40401)
    if lab.status != "active":
        raise AppError("该实验室已停用，无法预约")
    
    # ----- 4. 校区匹配检查 -----
    if int(payload["campus_id"]) != lab.campus_id:
        raise AppError("实验室与校区不匹配")

    # ----- 5. 时间解析与格式化 -----
    reservation_date = parse_date(payload["reservation_date"], "reservation_date")
    start_time = parse_time(payload["start_time"], "start_time")
    end_time = parse_time(payload["end_time"], "end_time")
    participant_count = int(payload.get("participant_count", 1))

    # ----- 6. 时间顺序校验 -----
    if start_time >= end_time:
        raise AppError("开始时间必须早于结束时间")
    
    # ----- 7. 开放时间范围校验 -----
    if start_time < lab.open_time or end_time > lab.close_time:
        raise AppError("预约时间必须在实验室开放时间范围内")
    
    # ----- 8. 人数上限校验 -----
    if participant_count > lab.capacity:
        raise AppError("参与人数超过实验室容量上限")

    # ----- 9. 时间冲突检查 -----
    overlapping = find_overlapping_reservation(
        lab.id, reservation_date, start_time, end_time
    )
    if overlapping:
        raise AppError("当前时间段已被占用，请选择其他时间")

    # ----- 10. 确定预约状态 -----
    # 普通用户（学生/教师）需要审批，管理员直接通过
    need_approval = current_user.role in {"student", "teacher"}
    status = "pending" if need_approval else "approved"

    # ----- 11. 创建预约记录 -----
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
    db.session.flush()  # 刷新以获取 reservation.id

    # ----- 12. 管理员自动审批记录 -----
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

    # ----- 13. 写操作日志 -----
    write_log(
        current_user.id,
        "reservation",
        "create",
        f"创建预约 #{reservation.id}，实验室 {lab.lab_name}，日期 {reservation_date.isoformat()}",
    )
    
    # ----- 14. 提交事务 -----
    db.session.commit()
    return reservation.to_dict()


# ==================== 取消预约 ====================
def cancel_reservation(current_user, reservation):
    """
    取消预约
    
    参数：
        current_user - 当前登录用户
        reservation  - 要取消的预约对象
    
    返回：
        取消后的预约对象字典
    
    权限规则：
        1. 预约状态必须是未取消/未驳回的
        2. 普通用户只能取消自己的预约
        3. 实验室管理员只能取消本校区的预约
        4. 系统管理员可以取消任何预约
    """
    # ----- 1. 状态检查：已取消/已驳回的不能再次取消 -----
    if reservation.status in {"cancelled", "rejected"}:
        raise AppError("当前预约状态不允许取消")
    
    # ----- 2. 权限检查：普通用户只能取消自己的 -----
    if current_user.role not in {"lab_admin", "system_admin"} and reservation.user_id != current_user.id:
        raise AppError("只能取消自己的预约", 403, 40303)
    
    # ----- 3. 权限检查：实验室管理员只能取消本校区的 -----
    if current_user.role == "lab_admin" and current_user.campus_id != reservation.campus_id:
        raise AppError("只能取消本校区的预约", 403, 40304)

    # ----- 4. 更新状态并记录日志 -----
    reservation.status = "cancelled"
    write_log(current_user.id, "reservation", "cancel", f"取消预约 #{reservation.id}")
    
    db.session.commit()
    return reservation.to_dict()


# ==================== 预约列表查询 ====================
def list_reservations(current_user, filters):
    """
    获取预约列表（带权限过滤）
    
    权限规则：
        - 学生/教师：只能看到自己的预约
        - 实验室管理员：只能看到自己校区的预约
        - 系统管理员：可以看到所有预约
    
    参数：
        current_user - 当前登录用户
        filters      - 筛选条件字典（status, campus_id, lab_id）
    
    返回：
        预约对象字典列表
    """
    # ----- 1. 基础查询（按创建时间倒序）-----
    query = Reservation.query.order_by(Reservation.created_at.desc())
    
    # ----- 2. 根据角色过滤数据范围 -----
    if current_user.role in {"student", "teacher"}:
        # 普通用户：只看自己的
        query = query.filter_by(user_id=current_user.id)
    elif current_user.role == "lab_admin":
        # 实验室管理员：只看本校区的
        query = query.filter_by(campus_id=current_user.campus_id)
    # 系统管理员：无额外过滤

    # ----- 3. 应用筛选条件 -----
    if filters.get("status"):
        query = query.filter_by(status=filters["status"])
    if filters.get("campus_id"):
        query = query.filter_by(campus_id=int(filters["campus_id"]))
    if filters.get("lab_id"):
        query = query.filter_by(lab_id=int(filters["lab_id"]))

    return [item.to_dict() for item in query.all()]


# ==================== 审批预约 ====================
def approve_reservation(current_user, reservation, approval_status, remark):
    """
    审批预约
    
    参数：
        current_user    - 当前登录用户（必须是管理员）
        reservation     - 待审批的预约对象
        approval_status - 审批结果（approved/rejected）
        remark          - 审批备注
    
    返回：
        审批后的预约对象字典（包含审批记录）
    
    权限规则：
        1. 只有管理员可以审批
        2. 实验室管理员只能审批本校区的预约
        3. 系统管理员可以审批任何预约
    
    特殊逻辑：
        审批通过前会再次检查时间冲突（防止并发审批导致的问题）
    """
    # ----- 1. 权限检查：必须是管理员 -----
    if current_user.role not in {"lab_admin", "system_admin"}:
        raise AppError("只有管理员可以审批预约", 403, 40305)
    
    # ----- 2. 权限检查：实验室管理员只能审批本校区 -----
    if current_user.role == "lab_admin" and current_user.campus_id != reservation.campus_id:
        raise AppError("只能审批本校区预约", 403, 40306)
    
    # ----- 3. 状态检查：只有 pending 状态的可以审批 -----
    if reservation.status != "pending":
        raise AppError("当前预约不在待审批状态")
    
    # ----- 4. 参数检查 -----
    if approval_status not in {"approved", "rejected"}:
        raise AppError("审批状态只能是 approved 或 rejected")

    # ----- 5. 审批通过时的冲突检查（防止并发穿透）-----
    # 场景：两个管理员同时审批同一个时间段的两个预约
    # 第一个通过后，第二个再通过时会被此检查拦截
    if approval_status == "approved":
        overlapping = find_overlapping_reservation(
            reservation.lab_id,
            reservation.reservation_date,
            reservation.start_time,
            reservation.end_time,
            exclude_id=reservation.id,  # 排除自己
        )
        if overlapping:
            raise AppError("审批失败，该时间段已有其他有效预约")

    # ----- 6. 更新预约状态 -----
    reservation.status = approval_status
    
    # ----- 7. 创建审批记录 -----
    approval = Approval(
        reservation_id=reservation.id,
        approver_id=current_user.id,
        approval_status=approval_status,
        remark=remark or "",
        approval_time=datetime.utcnow(),
    )
    db.session.add(approval)
    
    # ----- 8. 写操作日志 -----
    write_log(
        current_user.id,
        "approval",
        approval_status,
        f"审批预约 #{reservation.id}，结果 {approval_status}",
    )
    
    db.session.commit()
    return reservation.to_dict({"approval": approval.to_dict()})
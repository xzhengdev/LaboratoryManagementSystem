"""
预约管理蓝图 (reservation_bp)
功能：预约的创建、查询、取消等操作
权限：普通用户只能操作自己的预约，实验室管理员可查看本校区预约
"""

from flask import Blueprint, request           # Flask核心：蓝图、请求对象
from flask_jwt_extended import jwt_required   # JWT装饰器：要求请求携带有效令牌

from app.models import Reservation            # 预约数据模型
from app.services.rate_limit_service import enforce_create_reservation_rate_limit
from app.services.reservation_service import cancel_reservation, create_reservation, list_reservations  # 预约服务层
from app.utils.decorators import get_current_user  # 获取当前登录用户
from app.utils.exceptions import AppError      # 自定义异常类
from app.utils.response import success         # 统一成功响应格式

# ==================== 蓝图创建 ====================
reservation_bp = Blueprint("reservations", __name__)


# ==================== 创建预约 ====================
@reservation_bp.post("/reservations")
@jwt_required()  # 需要JWT认证（所有角色均可）
def create_reservation_api():
    """
    提交预约申请
    
    请求体示例：
        {
            "lab_id": 1,           // 实验室ID（必填）
            "reservation_date": "2024-01-15",  // 预约日期（必填）
            "start_time": "14:00", // 开始时间（必填）
            "end_time": "16:00",   // 结束时间（必填）
            "purpose": "实验课",    // 预约目的（可选）
            "participant_count": 30 // 参与人数（可选）
        }
    
    返回：
        新创建的预约对象（包含审批状态）
    """
    # 获取当前登录用户
    current_user = get_current_user()
    enforce_create_reservation_rate_limit(current_user.id)
    # 获取请求JSON，解析失败时返回空字典
    payload = request.get_json(silent=True) or {}
    idempotency_key = (request.headers.get("Idempotency-Key") or "").strip()
    # 调用服务层创建预约
    result = create_reservation(
        current_user,
        payload,
        idempotency_key=idempotency_key,
    )
    return success(result, "提交预约成功")


# ==================== 查看我的预约 ====================
@reservation_bp.get("/reservations/my")
@jwt_required()
def my_reservations():
    """
    查看当前用户自己的预约列表
    
    功能：
        - 学生/教师：看到自己提交的所有预约
        - 实验室管理员：看到自己校区内自己创建的预约
        - 系统管理员：看到自己创建的预约
    
    返回：
        预约列表数组
    """
    # 调用服务层获取预约列表（传入空字典表示无额外筛选条件）
    result = list_reservations(get_current_user(), {})
    return success(result)


# ==================== 查看预约详情 ====================
@reservation_bp.get("/reservations/<int:reservation_id>")
@jwt_required()
def reservation_detail(reservation_id):
    """
    查看单条预约的详细信息（包含审批记录）
    
    权限控制规则：
        - student/teacher：只能查看自己的预约
        - lab_admin：只能查看本校区的预约
        - system_admin：可以查看所有预约
    
    参数：
        reservation_id - 预约ID（URL路径参数）
    
    返回：
        预约详情字典，包含 approvals 字段（审批记录列表）
    """
    # 获取当前用户
    current_user = get_current_user()
    # 查询预约，不存在时自动返回404
    item = Reservation.query.get_or_404(reservation_id)
    
    # ----- 权限检查 -----
    # 普通用户（学生/教师）只能查看自己的预约
    if current_user.role in {"student", "teacher"} and item.user_id != current_user.id:
        raise AppError("只能查看自己的预约", 403, 40317)
    
    # 实验室管理员只能查看本校区的预约
    if current_user.role == "lab_admin" and current_user.campus_id != item.campus_id:
        raise AppError("只能查看本校区预约", 403, 40318)
    
    # 系统管理员无限制，可直接查看
    
    # 返回预约详情，包含关联的审批记录
    return success(item.to_dict({
        "approvals": [approval.to_dict() for approval in item.approvals]
    }))


# ==================== 取消预约 ====================
@reservation_bp.post("/reservations/<int:reservation_id>/cancel")
@jwt_required()
def cancel_reservation_api(reservation_id):
    """
    取消预约
    
    功能：
        - 用户可取消自己尚未开始的预约
        - 取消后预约状态变为 "cancelled"
    
    参数：
        reservation_id - 预约ID（URL路径参数）
    
    返回：
        取消后的预约信息
    """
    # 获取当前用户
    current_user = get_current_user()
    # 查询预约，不存在时自动返回404
    item = Reservation.query.get_or_404(reservation_id)
    # 调用服务层取消预约（内部会处理权限和状态验证）
    result = cancel_reservation(current_user, item)
    return success(result, "取消预约成功")


# ==================== 通用预约列表（管理端）====================
@reservation_bp.delete("/reservations/<int:reservation_id>")
@jwt_required()
def delete_reservation_api(reservation_id):
    current_user = get_current_user()
    item = Reservation.query.get_or_404(reservation_id)
    if item.user_id != current_user.id:
        raise AppError("只能删除自己的预约", 403, 40331)
    if item.status not in {"rejected", "cancelled"}:
        raise AppError("仅已拒绝或已取消的预约可删除", 400, 40071)

    from app.extensions import db
    from app.models import Approval

    Approval.query.filter_by(reservation_id=item.id).delete(synchronize_session=False)
    db.session.delete(item)
    db.session.commit()
    return success(None, "删除预约成功")


@reservation_bp.get("/reservations")
@jwt_required()
def list_reservations_api():
    """
    通用预约列表接口（管理端专用）
    
    功能：
        - 实验室管理员：查看本校区所有预约
        - 系统管理员：查看所有校区预约
        - 支持多种筛选条件
    
    支持的查询参数（通过 request.args 传入）：
        - lab_id      : 按实验室筛选
        - campus_id   : 按校区筛选
        - status      : 按状态筛选（pending/approved/rejected/cancelled）
        - start_date  : 开始日期筛选
        - end_date    : 结束日期筛选
        - user_id     : 按用户筛选（仅管理员可用）
        - page        : 页码（分页）
        - per_page    : 每页数量
    
    返回：
        预约列表数组（根据角色自动过滤）
    """
    # 调用服务层获取预约列表，传入请求参数作为筛选条件
    # 服务层会根据用户角色自动控制数据访问范围
    result = list_reservations(get_current_user(), request.args)
    return success(result)

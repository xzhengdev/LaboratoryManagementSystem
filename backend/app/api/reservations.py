from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from app.models import Reservation
from app.services.reservation_service import cancel_reservation, create_reservation, list_reservations
from app.utils.decorators import get_current_user
from app.utils.exceptions import AppError
from app.utils.response import success


reservation_bp = Blueprint("reservations", __name__)


@reservation_bp.post("/reservations")
@jwt_required()
def create_reservation_api():
    # 提交预约接口。
    current_user = get_current_user()
    payload = request.get_json(silent=True) or {}
    return success(create_reservation(current_user, payload), "提交预约成功")


@reservation_bp.get("/reservations/my")
@jwt_required()
def my_reservations():
    # 查看当前用户自己的预约列表。
    return success(list_reservations(get_current_user(), {}))


@reservation_bp.get("/reservations/<int:reservation_id>")
@jwt_required()
def reservation_detail(reservation_id):
    # 单条预约详情接口，并根据角色做访问控制。
    current_user = get_current_user()
    item = Reservation.query.get_or_404(reservation_id)
    if current_user.role in {"student", "teacher"} and item.user_id != current_user.id:
        raise AppError("只能查看自己的预约", 403, 40317)
    if current_user.role == "lab_admin" and current_user.campus_id != item.campus_id:
        raise AppError("只能查看本校区预约", 403, 40318)
    return success(item.to_dict({"approvals": [approval.to_dict() for approval in item.approvals]}))


@reservation_bp.post("/reservations/<int:reservation_id>/cancel")
@jwt_required()
def cancel_reservation_api(reservation_id):
    # 取消预约接口。
    current_user = get_current_user()
    item = Reservation.query.get_or_404(reservation_id)
    return success(cancel_reservation(current_user, item), "取消预约成功")


@reservation_bp.get("/reservations")
@jwt_required()
def list_reservations_api():
    # 通用预约列表接口，管理端可以借此查看更多预约记录。
    return success(list_reservations(get_current_user(), request.args))

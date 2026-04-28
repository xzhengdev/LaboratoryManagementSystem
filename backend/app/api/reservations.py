"""
预约管理蓝图 (reservation_bp)
功能：预约的创建、查询、取消等操作
"""

from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from app.services.rate_limit_service import enforce_create_reservation_rate_limit
from app.services.reservation_service import (
    cancel_reservation_by_id,
    create_reservation,
    delete_reservation_by_id,
    get_reservation_detail,
    list_reservations,
)
from app.utils.decorators import get_current_user
from app.utils.response import success


reservation_bp = Blueprint("reservations", __name__)


@reservation_bp.post("/reservations")
@jwt_required()
def create_reservation_api():
    current_user = get_current_user()
    enforce_create_reservation_rate_limit(current_user.id)
    payload = request.get_json(silent=True) or {}
    idempotency_key = (request.headers.get("Idempotency-Key") or "").strip()
    result = create_reservation(
        current_user,
        payload,
        idempotency_key=idempotency_key,
    )
    return success(result, "提交预约成功")


@reservation_bp.get("/reservations/my")
@jwt_required()
def my_reservations():
    result = list_reservations(get_current_user(), {})
    return success(result)


@reservation_bp.get("/reservations/<int:reservation_id>")
@jwt_required()
def reservation_detail(reservation_id):
    current_user = get_current_user()
    result = get_reservation_detail(current_user, reservation_id)
    return success(result)


@reservation_bp.post("/reservations/<int:reservation_id>/cancel")
@jwt_required()
def cancel_reservation_api(reservation_id):
    current_user = get_current_user()
    result = cancel_reservation_by_id(current_user, reservation_id)
    return success(result, "取消预约成功")


@reservation_bp.delete("/reservations/<int:reservation_id>")
@jwt_required()
def delete_reservation_api(reservation_id):
    current_user = get_current_user()
    delete_reservation_by_id(current_user, reservation_id)
    return success(None, "删除预约成功")


@reservation_bp.get("/reservations")
@jwt_required()
def list_reservations_api():
    result = list_reservations(get_current_user(), request.args)
    return success(result)

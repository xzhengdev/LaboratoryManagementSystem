from flask import Blueprint, request

from app.services.rate_limit_service import enforce_approve_reservation_rate_limit
from app.services.reservation_service import approve_reservation_by_id, list_pending_approvals
from app.utils.decorators import get_current_user, role_required
from app.utils.response import success


approval_bp = Blueprint("approvals", __name__)


@approval_bp.get("/approvals/pending")
@role_required("lab_admin", "system_admin")
def pending_approvals():
    current_user = get_current_user()
    result = list_pending_approvals(current_user)
    return success(result)


@approval_bp.post("/approvals/<int:reservation_id>")
@role_required("lab_admin", "system_admin")
def approve_api(reservation_id):
    payload = request.get_json(silent=True) or {}
    current_user = get_current_user()
    enforce_approve_reservation_rate_limit(current_user.id)
    data = approve_reservation_by_id(
        current_user,
        reservation_id,
        payload.get("approval_status", ""),
        payload.get("remark", ""),
    )
    return success(data, "审批完成")

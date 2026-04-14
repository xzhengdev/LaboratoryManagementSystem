from flask import Blueprint, request

from app.models import Reservation
from app.services.reservation_service import approve_reservation
from app.utils.decorators import get_current_user, role_required
from app.utils.response import success


approval_bp = Blueprint("approvals", __name__)


@approval_bp.get("/approvals/pending")
@role_required("lab_admin", "system_admin")
def pending_approvals():
    # 待审批预约列表接口。
    current_user = get_current_user()
    query = Reservation.query.filter_by(status="pending").order_by(Reservation.created_at.desc())
    if current_user.role == "lab_admin":
        query = query.filter_by(campus_id=current_user.campus_id)
    return success([item.to_dict() for item in query.all()])


@approval_bp.post("/approvals/<int:reservation_id>")
@role_required("lab_admin", "system_admin")
def approve_api(reservation_id):
    # 审批动作接口：approval_status 取 approved 或 rejected。
    payload = request.get_json(silent=True) or {}
    item = Reservation.query.get_or_404(reservation_id)
    data = approve_reservation(
        get_current_user(),
        item,
        payload.get("approval_status", ""),
        payload.get("remark", ""),
    )
    return success(data, "审批完成")

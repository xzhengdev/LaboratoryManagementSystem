from flask import Blueprint

from app.services.statistics_service import get_campus_statistics, get_lab_usage, get_overview
from app.utils.decorators import get_current_user, role_required
from app.utils.response import success


statistics_bp = Blueprint("statistics", __name__)


@statistics_bp.get("/statistics/overview")
@role_required("lab_admin", "system_admin")
def overview_api():
    current_user = get_current_user()
    campus_id = current_user.campus_id if current_user.role == "lab_admin" else None
    return success(get_overview(campus_id=campus_id))


@statistics_bp.get("/statistics/campus")
@role_required("lab_admin", "system_admin")
def campus_statistics_api():
    current_user = get_current_user()
    campus_id = current_user.campus_id if current_user.role == "lab_admin" else None
    return success(get_campus_statistics(campus_id=campus_id))


@statistics_bp.get("/statistics/lab_usage")
@role_required("lab_admin", "system_admin")
def lab_usage_api():
    current_user = get_current_user()
    campus_id = current_user.campus_id if current_user.role == "lab_admin" else None
    return success(get_lab_usage(campus_id=campus_id))

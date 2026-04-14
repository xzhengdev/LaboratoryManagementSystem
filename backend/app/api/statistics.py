from flask import Blueprint

from app.services.statistics_service import get_campus_statistics, get_lab_usage, get_overview
from app.utils.decorators import role_required
from app.utils.response import success


statistics_bp = Blueprint("statistics", __name__)


@statistics_bp.get("/statistics/overview")
@role_required("lab_admin", "system_admin")
def overview_api():
    # 总览统计接口。
    return success(get_overview())


@statistics_bp.get("/statistics/campus")
@role_required("lab_admin", "system_admin")
def campus_statistics_api():
    # 校区维度统计接口。
    return success(get_campus_statistics())


@statistics_bp.get("/statistics/lab_usage")
@role_required("lab_admin", "system_admin")
def lab_usage_api():
    # 实验室使用情况统计接口。
    return success(get_lab_usage())

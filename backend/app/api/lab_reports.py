from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from app.models import LabDailyReport, Laboratory
from app.services.db_router_service import campus_db_session, get_routed_campus_ids
from app.services.file_storage_service import save_image_file
from app.services.lab_report_service import (
    create_daily_report,
    list_daily_reports,
    review_daily_report,
)
from app.services.rate_limit_service import enforce_submit_daily_report_rate_limit
from app.utils.decorators import get_current_user, role_required
from app.utils.exceptions import AppError
from app.utils.response import success


lab_report_bp = Blueprint("lab_reports", __name__)


def _campus_candidates_for_user(current_user):
    if current_user.role == "system_admin":
        candidates = get_routed_campus_ids()
        return candidates or [0]
    return [current_user.campus_id or 0]


def _find_lab_and_campus(current_user, lab_id):
    for campus_id in _campus_candidates_for_user(current_user):
        with campus_db_session(campus_id) as session:
            lab = session.query(Laboratory).get(int(lab_id))
            if lab:
                return campus_id, lab
    raise AppError("实验室不存在", 404, 40401)


def _find_report(current_user, report_id):
    for campus_id in _campus_candidates_for_user(current_user):
        with campus_db_session(campus_id) as session:
            item = session.query(LabDailyReport).get(int(report_id))
            if item:
                return item
    raise AppError("日报不存在", 404, 40413)


@lab_report_bp.post("/lab-reports/photos/upload")
@jwt_required()
def upload_daily_report_photo_api():
    current_user = get_current_user()
    file_storage = request.files.get("file")
    if not file_storage:
        raise AppError("缺少文件字段 file")

    campus_id = request.form.get("campus_id")
    lab_id = request.form.get("lab_id")

    if campus_id:
        target_campus_id = int(campus_id)
    elif lab_id:
        target_campus_id, _ = _find_lab_and_campus(current_user, lab_id)
    else:
        target_campus_id = current_user.campus_id

    if not target_campus_id:
        raise AppError("无法确定图片所属校区")

    if current_user.role != "system_admin" and current_user.campus_id != target_campus_id:
        raise AppError("只能上传本校区日报图片", 403, 40356)

    with campus_db_session(target_campus_id) as session:
        file_obj = save_image_file(
            current_user=current_user,
            file_storage=file_storage,
            campus_id=target_campus_id,
            biz_type="daily_report_temp",
            biz_id=None,
            session=session,
        )
        session.commit()
        return success(file_obj.to_dict(), "日报图片上传成功")


@lab_report_bp.post("/lab-reports")
@jwt_required()
def create_daily_report_api():
    current_user = get_current_user()
    enforce_submit_daily_report_rate_limit(current_user.id)
    payload = request.get_json(silent=True) or {}
    result = create_daily_report(current_user, payload)
    return success(result, "日报提交成功")


@lab_report_bp.get("/lab-reports")
@jwt_required()
def list_daily_reports_api():
    current_user = get_current_user()
    result = list_daily_reports(current_user, request.args)
    return success(result)


@lab_report_bp.post("/lab-reports/<int:report_id>/review")
@role_required("lab_admin", "system_admin")
def review_daily_report_api(report_id):
    current_user = get_current_user()
    payload = request.get_json(silent=True) or {}
    item = _find_report(current_user, report_id)
    result = review_daily_report(
        current_user,
        item,
        payload.get("review_status", ""),
        payload.get("review_remark", ""),
    )
    return success(result, "日报审核完成")

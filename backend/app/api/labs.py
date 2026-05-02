"""
实验室管理蓝图 (lab_bp)
"""
from datetime import datetime
import json
import os
import imghdr
from uuid import uuid4

from flask import Blueprint, request, current_app
from flask_jwt_extended import jwt_required
from sqlalchemy.exc import IntegrityError
from werkzeug.utils import secure_filename

from app.models import Approval, Equipment, Laboratory, Reservation
from app.services.cache_service import invalidate_lab_schedule_cache, invalidate_statistics_cache
from app.services.reservation_service import get_lab_schedule
from app.services.db_router_service import (
    campus_db_session,
    find_across_campuses,
    get_routed_campus_ids,
    aggregate_across_campuses,
)
from app.services.file_storage_service import save_image_file
from app.utils.decorators import get_current_user, role_required
from app.utils.exceptions import AppError
from app.utils.response import success
from app.utils.validators import parse_date, parse_time, require_fields

lab_bp = Blueprint("labs", __name__)

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MIMETYPE_EXT_MAP = {"image/jpeg": "jpg", "image/jpg": "jpg", "image/png": "png", "image/webp": "webp"}
IMGHDR_EXT_MAP = {"jpeg": "jpg", "png": "png", "webp": "webp"}


def _reservation_can_cleanup(item, now):
    if item.status in {"cancelled", "rejected"}:
        return True
    end_at = datetime.combine(item.reservation_date, item.end_time)
    return end_at <= now


def _normalize_photos(value):
    if value in (None, ""):
        return "[]"
    data = value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return "[]"
        try:
            data = json.loads(text)
        except Exception:
            raise AppError("photos must be array or valid JSON string", 400, 40041)
    if not isinstance(data, list):
        raise AppError("photos must be array", 400, 40042)
    cleaned = []
    for item in data:
        if item in (None, ""):
            continue
        url = str(item).strip()
        if not url:
            continue
        if len(url) > 500:
            raise AppError("photo URL too long (max 500)", 400, 40043)
        cleaned.append(url)
    if len(cleaned) > 20:
        raise AppError("max 20 photos", 400, 40044)
    return json.dumps(cleaned, ensure_ascii=False)


@lab_bp.get("/labs")
@jwt_required()
def list_labs():
    campus_id = request.args.get("campus_id")
    if campus_id:
        with campus_db_session(int(campus_id)) as session:
            query = session.query(Laboratory).order_by(Laboratory.id.asc())
            if request.args.get("status"):
                query = query.filter_by(status=request.args["status"])
            items = [item.to_dict() for item in query.all()]
    else:
        def _query(session):
            q = session.query(Laboratory).order_by(Laboratory.id.asc())
            if request.args.get("status"):
                q = q.filter_by(status=request.args["status"])
            return [item.to_dict() for item in q.all()]
        items = aggregate_across_campuses(Laboratory, _query)
    return success(items)


@lab_bp.get("/labs/<int:lab_id>")
@jwt_required()
def lab_detail(lab_id):
    item, campus_id = find_across_campuses(Laboratory, lab_id)
    if not item:
        raise AppError("lab not found", 404, 40401)
    with campus_db_session(campus_id) as session:
        lab = session.get(Laboratory, lab_id)
        result = lab.to_dict({"equipment": [eq.to_dict() for eq in lab.equipment]})
    return success(result)


@lab_bp.get("/labs/<int:lab_id>/schedule")
@jwt_required()
def lab_schedule(lab_id):
    item, _ = find_across_campuses(Laboratory, lab_id)
    if not item:
        raise AppError("lab not found", 404, 40401)
    date_str = request.args.get("date")
    if not date_str:
        raise AppError("date param required")
    return success(get_lab_schedule(item, parse_date(date_str, "date")))


@lab_bp.post("/labs")
@role_required("lab_admin", "system_admin")
def create_lab():
    current_user = get_current_user()
    payload = request.get_json(silent=True) or {}
    require_fields(payload, ["campus_id", "lab_name", "location", "capacity", "open_time", "close_time"])
    campus_id = int(payload["campus_id"])
    if current_user.role == "lab_admin" and current_user.campus_id != campus_id:
        raise AppError("can only manage own campus labs", 403, 40310)
    with campus_db_session(campus_id) as session:
        item = Laboratory(
            campus_id=campus_id,
            lab_name=payload["lab_name"],
            location=payload["location"],
            capacity=int(payload["capacity"]),
            open_time=parse_time(payload["open_time"], "open_time"),
            close_time=parse_time(payload["close_time"], "close_time"),
            status=payload.get("status", "active"),
            description=payload.get("description", ""),
            photos=_normalize_photos(payload.get("photos")),
        )
        session.add(item)
        session.commit()
        result = item.to_dict()
    invalidate_statistics_cache()
    return success(result, "lab created")


@lab_bp.put("/labs/<int:lab_id>")
@role_required("lab_admin", "system_admin")
def update_lab(lab_id):
    current_user = get_current_user()
    payload = request.get_json(silent=True) or {}
    item, campus_id = find_across_campuses(Laboratory, lab_id)
    if not item:
        raise AppError("lab not found", 404, 40401)
    if current_user.role == "lab_admin" and current_user.campus_id != item.campus_id:
        raise AppError("can only update own campus labs", 403, 40311)
    with campus_db_session(item.campus_id) as session:
        lab = session.get(Laboratory, lab_id)
        for field in ["lab_name", "location", "status", "description"]:
            if field in payload:
                setattr(lab, field, payload[field])
        if "photos" in payload:
            lab.photos = _normalize_photos(payload.get("photos"))
        if "campus_id" in payload:
            new_cid = int(payload["campus_id"])
            if current_user.role == "lab_admin" and current_user.campus_id != new_cid:
                raise AppError("cannot transfer lab to other campus", 403, 40312)
            lab.campus_id = new_cid
        if "capacity" in payload:
            lab.capacity = int(payload["capacity"])
        if "open_time" in payload:
            lab.open_time = parse_time(payload["open_time"], "open_time")
        if "close_time" in payload:
            lab.close_time = parse_time(payload["close_time"], "close_time")
        session.commit()
        result = lab.to_dict()
    invalidate_lab_schedule_cache(lab_id)
    invalidate_statistics_cache()
    return success(result, "lab updated")


@lab_bp.post("/labs/upload-photo")
@role_required("lab_admin", "system_admin")
def upload_lab_photo():
    current_user = get_current_user()
    file_storage = request.files.get("file")
    if not file_storage:
        raise AppError("file required", 400, 40071)
    campus_id_text = str(request.form.get("campus_id") or "").strip()
    campus_id = int(campus_id_text) if campus_id_text else current_user.campus_id
    if not campus_id:
        raise AppError("campus_id required", 400, 40074)
    if current_user.role == "lab_admin" and current_user.campus_id != campus_id:
        raise AppError("can only upload for own campus", 403, 40312)
    lab_id_text = str(request.form.get("lab_id") or "").strip()
    lab_id = int(lab_id_text) if lab_id_text else None
    with campus_db_session(campus_id) as session:
        file_obj = save_image_file(
            current_user=current_user, file_storage=file_storage,
            campus_id=campus_id, biz_type="lab_photo", biz_id=lab_id, session=session,
        )
        session.commit()
        return success(file_obj.to_dict(), "photo uploaded")


@lab_bp.delete("/labs/<int:lab_id>")
@role_required("lab_admin", "system_admin")
def delete_lab(lab_id):
    current_user = get_current_user()
    item, _ = find_across_campuses(Laboratory, lab_id)
    if not item:
        raise AppError("lab not found", 404, 40401)
    if current_user.role == "lab_admin" and current_user.campus_id != item.campus_id:
        raise AppError("can only delete own campus labs", 403, 40313)
    with campus_db_session(item.campus_id) as session:
        reservations = session.query(Reservation).filter_by(lab_id=lab_id).all()
        now = datetime.now()
        blocking = [r for r in reservations if not _reservation_can_cleanup(r, now)]
        if blocking:
            raise AppError(f"{len(blocking)} active reservations prevent deletion", 400, 40031)
        for r in reservations:
            session.query(Approval).filter_by(reservation_id=r.id).delete(synchronize_session=False)
            session.delete(r)
        for eq in session.query(Equipment).filter_by(lab_id=lab_id).all():
            session.delete(eq)
        lab = session.get(Laboratory, lab_id)
        session.delete(lab)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            raise AppError("lab has related data, cannot delete", 400, 40032)
    invalidate_lab_schedule_cache(lab_id)
    invalidate_statistics_cache()
    return success(message="lab deleted")

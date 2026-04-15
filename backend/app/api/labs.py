from datetime import datetime
import json
import os
import imghdr
from uuid import uuid4

from flask import Blueprint, request, current_app
from flask_jwt_extended import jwt_required
from sqlalchemy.exc import IntegrityError
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import Approval, Equipment, Laboratory, Reservation
from app.services.reservation_service import get_lab_schedule
from app.utils.decorators import get_current_user, role_required
from app.utils.exceptions import AppError
from app.utils.response import success
from app.utils.validators import parse_date, parse_time, require_fields


lab_bp = Blueprint("labs", __name__)
ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MIMETYPE_EXT_MAP = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}
IMGHDR_EXT_MAP = {
    "jpeg": "jpg",
    "png": "png",
    "webp": "webp",
}


def _reservation_can_cleanup(item, now):
    # 可清理预约定义：
    # 1) 已取消/已驳回
    # 2) 已经过了结束时间（预约结束）
    if item.status in {"cancelled", "rejected"}:
        return True
    end_at = datetime.combine(item.reservation_date, item.end_time)
    return end_at <= now


def _normalize_photos(value):
    # 允许前端传数组或 JSON 字符串，统一存储为 JSON 字符串。
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
            raise AppError("photos 必须是数组或合法 JSON 字符串", 400, 40041)
    if not isinstance(data, list):
        raise AppError("photos 必须是数组", 400, 40042)

    cleaned = []
    for item in data:
        if item in (None, ""):
            continue
        url = str(item).strip()
        if not url:
            continue
        if len(url) > 500:
            raise AppError("单张实验室照片地址长度不能超过 500", 400, 40043)
        cleaned.append(url)

    if len(cleaned) > 20:
        raise AppError("实验室照片最多支持 20 张", 400, 40044)
    return json.dumps(cleaned, ensure_ascii=False)


@lab_bp.get("/labs")
@jwt_required()
def list_labs():
    # 实验室列表接口，支持按校区和状态筛选。
    query = Laboratory.query.order_by(Laboratory.id.asc())
    if request.args.get("campus_id"):
        query = query.filter_by(campus_id=int(request.args["campus_id"]))
    if request.args.get("status"):
        query = query.filter_by(status=request.args["status"])
    return success([item.to_dict() for item in query.all()])


@lab_bp.get("/labs/<int:lab_id>")
@jwt_required()
def lab_detail(lab_id):
    # 实验室详情接口，附带设备清单。
    item = Laboratory.query.get_or_404(lab_id)
    return success(item.to_dict({"equipment": [eq.to_dict() for eq in item.equipment]}))


@lab_bp.get("/labs/<int:lab_id>/schedule")
@jwt_required()
def lab_schedule(lab_id):
    # 查询实验室某一天排期，是预约页和 Agent 的核心接口之一。
    item = Laboratory.query.get_or_404(lab_id)
    date_str = request.args.get("date")
    if not date_str:
        raise AppError("请传入 date 参数")
    return success(get_lab_schedule(item, parse_date(date_str, "date")))


@lab_bp.post("/labs")
@role_required("lab_admin", "system_admin")
def create_lab():
    # 实验室新增：
    # 系统管理员可操作全部校区；
    # 实验室管理员只能操作自己所属校区。
    current_user = get_current_user()
    payload = request.get_json(silent=True) or {}
    require_fields(
        payload,
        ["campus_id", "lab_name", "location", "capacity", "open_time", "close_time"],
    )
    campus_id = int(payload["campus_id"])
    if current_user.role == "lab_admin" and current_user.campus_id != campus_id:
        raise AppError("只能管理本校区实验室", 403, 40310)
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
    db.session.add(item)
    db.session.commit()
    return success(item.to_dict(), "创建实验室成功")


@lab_bp.put("/labs/<int:lab_id>")
@role_required("lab_admin", "system_admin")
def update_lab(lab_id):
    # 实验室更新接口，权限规则同新增。
    current_user = get_current_user()
    payload = request.get_json(silent=True) or {}
    item = Laboratory.query.get_or_404(lab_id)
    if current_user.role == "lab_admin" and current_user.campus_id != item.campus_id:
        raise AppError("只能更新本校区实验室", 403, 40311)

    for field in ["lab_name", "location", "status", "description"]:
        if field in payload:
            setattr(item, field, payload[field])
    if "photos" in payload:
        item.photos = _normalize_photos(payload.get("photos"))
    if "campus_id" in payload:
        campus_id = int(payload["campus_id"])
        if current_user.role == "lab_admin" and current_user.campus_id != campus_id:
            raise AppError("不能把实验室转移到其他校区", 403, 40312)
        item.campus_id = campus_id
    if "capacity" in payload:
        item.capacity = int(payload["capacity"])
    if "open_time" in payload:
        item.open_time = parse_time(payload["open_time"], "open_time")
    if "close_time" in payload:
        item.close_time = parse_time(payload["close_time"], "close_time")
    db.session.commit()
    return success(item.to_dict(), "更新实验室成功")


@lab_bp.post("/labs/upload-photo")
@role_required("lab_admin", "system_admin")
def upload_lab_photo():
    if "file" not in request.files:
        raise AppError("请上传实验室封面文件", 400, 40071)

    file = request.files["file"]
    if not file or not file.filename:
        raise AppError("实验室封面文件无效", 400, 40072)

    filename = secure_filename(file.filename)
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    mime = (file.mimetype or "").lower()

    if not ext:
        ext = MIMETYPE_EXT_MAP.get(mime, "")
    if not ext and mime.startswith("image/"):
        sub = mime.split("/", 1)[1].split(";", 1)[0].strip()
        if sub == "jpeg":
            sub = "jpg"
        ext = sub
    if not ext:
        detected = imghdr.what(file.stream)
        if detected:
            ext = IMGHDR_EXT_MAP.get(detected, detected)
        file.stream.seek(0)
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise AppError("仅支持 jpg/jpeg/png/webp 格式", 400, 40073)

    save_name = f"{uuid4().hex}.{ext}"
    relative_path = os.path.join("labs", save_name)
    absolute_path = os.path.join(current_app.config["UPLOAD_ROOT"], relative_path)
    file.save(absolute_path)

    public_path = f"/uploads/{relative_path.replace(os.sep, '/')}"
    public_url = f"{request.host_url.rstrip('/')}{public_path}"
    return success({"url": public_url, "path": public_path}, "实验室封面上传成功")


@lab_bp.delete("/labs/<int:lab_id>")
@role_required("lab_admin", "system_admin")
def delete_lab(lab_id):
    # 实验室删除接口，权限规则同新增。
    current_user = get_current_user()
    item = Laboratory.query.get_or_404(lab_id)
    if current_user.role == "lab_admin" and current_user.campus_id != item.campus_id:
        raise AppError("只能删除本校区实验室", 403, 40313)

    reservations = Reservation.query.filter_by(lab_id=item.id).all()
    now = datetime.now()
    blocking = [r for r in reservations if not _reservation_can_cleanup(r, now)]
    if blocking:
        raise AppError(
            f"该实验室下仍有 {len(blocking)} 条未结束预约，无法删除",
            400,
            40031,
        )

    # 所有预约都满足“可清理”后，按依赖顺序删除：
    # 审批记录 -> 预约 -> 设备 -> 实验室
    for reservation in reservations:
        Approval.query.filter_by(reservation_id=reservation.id).delete(
            synchronize_session=False
        )
        db.session.delete(reservation)

    equipment_items = Equipment.query.filter_by(lab_id=item.id).all()
    for equipment in equipment_items:
        db.session.delete(equipment)

    db.session.delete(item)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise AppError("该实验室存在关联数据，无法删除", 400, 40032)
    return success(message="删除实验室成功")

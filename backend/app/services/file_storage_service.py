import hashlib
import os
from datetime import datetime
from uuid import uuid4

import requests
from flask import current_app
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import FileObject, Laboratory
from app.services.event_bus_service import publish_async_event
from app.utils.exceptions import AppError

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
IMAGE_MIME_PREFIX = "image/"


def _safe_filename(filename):
    name = secure_filename(filename or "")
    return name or f"upload-{uuid4().hex}.bin"


def _validate_image(file_storage):
    filename = _safe_filename(file_storage.filename)
    ext = os.path.splitext(filename)[1].lower()
    mime_type = file_storage.mimetype or "application/octet-stream"
    if ext not in IMAGE_EXTENSIONS or not mime_type.startswith(IMAGE_MIME_PREFIX):
        raise AppError("仅支持上传 jpg、png、gif、webp 格式图片")
    return filename, mime_type


def _save_local(file_bytes, filename, campus_id, biz_type):
    upload_root = current_app.config["UPLOAD_ROOT"]
    day = datetime.utcnow().strftime("%Y%m%d")
    relative_dir = os.path.join("distributed-files", str(campus_id), biz_type, day)
    target_dir = os.path.join(upload_root, relative_dir)
    os.makedirs(target_dir, exist_ok=True)

    ext = os.path.splitext(filename)[1].lower()
    stored_name = f"{uuid4().hex}{ext}"
    relative_path = os.path.join(relative_dir, stored_name).replace("\\", "/")
    absolute_path = os.path.join(upload_root, relative_path)
    with open(absolute_path, "wb") as target:
        target.write(file_bytes)
    return {
        "storage_backend": "local",
        "file_id": relative_path,
        "url": f"/uploads/{relative_path}",
    }


def _save_seaweedfs(file_bytes, filename):
    upload_url = str(current_app.config.get("SEAWEEDFS_UPLOAD_URL", "")).strip()
    public_base_url = str(current_app.config.get("SEAWEEDFS_PUBLIC_URL", "")).strip().rstrip("/")
    if not upload_url:
        return None

    try:
        response = requests.post(
            upload_url,
            files={"file": (filename, file_bytes)},
            timeout=float(current_app.config.get("SEAWEEDFS_TIMEOUT_SECONDS", 8)),
        )
        response.raise_for_status()
        data = response.json() if response.content else {}
    except Exception as exc:
        raise AppError(f"SeaweedFS 上传失败: {exc}", 502, 50231)

    file_id = str(data.get("fid") or data.get("file_id") or data.get("name") or "").strip()
    if not file_id:
        raise AppError("SeaweedFS 未返回文件标识", 502, 50232)
    url = data.get("url") or f"{public_base_url}/{file_id}" if public_base_url else file_id
    return {
        "storage_backend": "seaweedfs",
        "file_id": file_id,
        "url": url,
    }


def user_can_access_file(current_user, file_object):
    if current_user.role == "system_admin":
        return True
    if current_user.role == "lab_admin":
        return current_user.campus_id == file_object.campus_id
    return current_user.id == file_object.created_by


def save_image_file(current_user, file_storage, campus_id, biz_type, biz_id=None, session=None):
    filename, mime_type = _validate_image(file_storage)
    file_bytes = file_storage.read()
    if not file_bytes:
        raise AppError("上传文件不能为空")

    max_size = int(current_app.config.get("MAX_CONTENT_LENGTH", 10 * 1024 * 1024))
    if len(file_bytes) > max_size:
        raise AppError("上传文件过大，请控制在 10MB 以内", 413, 41300)

    digest = hashlib.sha256(file_bytes).hexdigest()
    storage_result = _save_seaweedfs(file_bytes, filename) or _save_local(
        file_bytes, filename, campus_id, biz_type
    )

    active_session = session or db.session

    item = FileObject(
        campus_id=int(campus_id),
        biz_type=biz_type,
        biz_id=biz_id,
        file_id=storage_result["file_id"],
        original_name=filename,
        storage_backend=storage_result["storage_backend"],
        url=storage_result["url"],
        mime_type=mime_type,
        size=len(file_bytes),
        sha256=digest,
        created_by=current_user.id,
    )
    active_session.add(item)
    active_session.flush()
    publish_async_event(
        "file.uploaded",
        {
            "file_object_id": item.id,
            "campus_id": item.campus_id,
            "biz_type": item.biz_type,
            "biz_id": item.biz_id,
            "storage_backend": item.storage_backend,
            "file_id": item.file_id,
        },
    )
    return item


def infer_lab_campus(lab_id, session=None):
    active_session = session or db.session
    lab = active_session.query(Laboratory).get(int(lab_id))
    if not lab:
        raise AppError("实验室不存在", 404, 40401)
    return lab, lab.campus_id

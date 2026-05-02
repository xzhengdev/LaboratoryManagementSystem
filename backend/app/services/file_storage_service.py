"""
文件上传服务模块
支持本地存储和 SeaweedFS 分布式存储，提供图片上传、权限校验等功能
"""

import hashlib
import json
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

# 支持的图片格式
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
IMAGE_MIME_PREFIX = "image/"


def _safe_filename(filename):
    """生成安全的文件名，防止路径遍历攻击"""
    name = secure_filename(filename or "")
    return name or f"upload-{uuid4().hex}.bin"


def _validate_image(file_storage):
    """校验文件是否为合法图片格式"""
    filename = _safe_filename(file_storage.filename)
    ext = os.path.splitext(filename)[1].lower()
    mime_type = file_storage.mimetype or "application/octet-stream"
    if ext not in IMAGE_EXTENSIONS or not mime_type.startswith(IMAGE_MIME_PREFIX):
        raise AppError("仅支持上传 jpg、png、gif、webp 格式图片")
    return filename, mime_type


def _save_local(file_bytes, filename, campus_id, biz_type):
    """保存文件到本地存储"""
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


def _parse_campus_seaweedfs_map():
    """解析校区 SeaweedFS 配置映射"""
    raw = str(current_app.config.get("SEAWEEDFS_CAMPUS_CONFIG_MAP", "")).strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except Exception:
        current_app.logger.warning("SEAWEEDFS_CAMPUS_CONFIG_MAP 不是合法 JSON，已忽略")
        return {}

    result = {}
    for key, value in (data or {}).items():
        try:
            campus_id = int(key)
        except Exception:
            continue

        if isinstance(value, str):
            upload_url = value.strip()
            public_url = ""
            timeout_seconds = None
        else:
            upload_url = str((value or {}).get("upload_url") or "").strip()
            public_url = str((value or {}).get("public_url") or "").strip()
            write_url = str((value or {}).get("write_url") or "").strip()
            raw_timeout = (value or {}).get("timeout_seconds")
            try:
                timeout_seconds = float(raw_timeout) if raw_timeout is not None else None
            except Exception:
                timeout_seconds = None

        if not upload_url:
            continue

        result[campus_id] = {
            "upload_url": upload_url,
            "public_url": public_url.rstrip("/"),
            "write_url": write_url.rstrip("/"),
            "timeout_seconds": timeout_seconds,
        }
    return result


def _resolve_seaweedfs_target(campus_id):
    """根据校区获取 SeaweedFS 上传目标配置"""
    campus_map = _parse_campus_seaweedfs_map()
    try:
        cid = int(campus_id)
    except Exception:
        cid = None

    if cid is not None and cid in campus_map:
        row = campus_map[cid]
        timeout = row.get("timeout_seconds")
        if timeout is None:
            timeout = float(current_app.config.get("SEAWEEDFS_TIMEOUT_SECONDS", 8))
        return row["upload_url"], row.get("public_url", ""), row.get("write_url", ""), float(timeout)

    upload_url = str(current_app.config.get("SEAWEEDFS_UPLOAD_URL", "")).strip()
    public_base_url = str(current_app.config.get("SEAWEEDFS_PUBLIC_URL", "")).strip().rstrip("/")
    write_base_url = str(current_app.config.get("SEAWEEDFS_WRITE_URL", "")).strip().rstrip("/")
    timeout_seconds = float(current_app.config.get("SEAWEEDFS_TIMEOUT_SECONDS", 8))
    return upload_url, public_base_url, write_base_url, timeout_seconds


def _save_seaweedfs(file_bytes, filename, campus_id):
    """保存文件到 SeaweedFS 分布式存储"""
    upload_url, public_base_url, write_base_url, timeout_seconds = _resolve_seaweedfs_target(campus_id)
    if not upload_url:
        return None

    upload_url = upload_url.rstrip("/")

    # 兼容旧配置：直接 POST 到 /submit
    if upload_url.endswith("/submit"):
        try:
            response = requests.post(
                upload_url,
                files={"file": (filename, file_bytes)},
                timeout=timeout_seconds,
            )
            response.raise_for_status()
            data = response.json() if response.content else {}
        except Exception as exc:
            raise AppError(f"SeaweedFS 上传失败: {exc}", 502, 50231)

        file_id = str(data.get("fid") or data.get("file_id") or data.get("name") or "").strip()
        if not file_id:
            raise AppError("SeaweedFS 未返回文件标识", 502, 50232)

        if data.get("url"):
            url = str(data.get("url")).strip()
        elif public_base_url:
            url = f"{public_base_url}/{file_id}"
        else:
            url = file_id

        return {
            "storage_backend": "seaweedfs",
            "file_id": file_id,
            "url": url,
        }

    # 新流程：先向 master 申请 fid，再写入 volume 节点
    try:
        assign_resp = requests.get(
            f"{upload_url}/dir/assign",
            timeout=timeout_seconds,
        )
        assign_resp.raise_for_status()
        assign_data = assign_resp.json() if assign_resp.content else {}
    except Exception as exc:
        raise AppError(f"SeaweedFS 分配文件ID失败: {exc}", 502, 50231)

    file_id = str(assign_data.get("fid") or "").strip()
    if not file_id:
        raise AppError("SeaweedFS 未返回 fid", 502, 50232)

    candidates = []
    if write_base_url:
        candidates.append(f"{write_base_url}/{file_id}")
    raw_write_target = str(assign_data.get("url") or "").strip()
    if raw_write_target:
        if raw_write_target.startswith("http://") or raw_write_target.startswith("https://"):
            candidates.append(f"{raw_write_target.rstrip('/')}/{file_id}")
        else:
            candidates.append(f"http://{raw_write_target.rstrip('/')}/{file_id}")
    if public_base_url:
        candidates.append(f"{public_base_url}/{file_id}")

    last_error = None
    for target in candidates:
        try:
            write_resp = requests.post(
                target,
                files={"file": (filename, file_bytes)},
                timeout=timeout_seconds,
            )
            write_resp.raise_for_status()
            last_error = None
            break
        except Exception as exc:
            last_error = exc
            continue
    if last_error is not None:
        raise AppError(f"SeaweedFS 写入失败: {last_error}", 502, 50233)

    raw_public = str(assign_data.get("publicUrl") or "").strip()
    if public_base_url:
        url = f"{public_base_url}/{file_id}"
    elif raw_public:
        if raw_public.startswith("http://") or raw_public.startswith("https://"):
            url = f"{raw_public.rstrip('/')}/{file_id}"
        else:
            url = f"http://{raw_public.rstrip('/')}/{file_id}"
    else:
        url = file_id

    return {
        "storage_backend": "seaweedfs",
        "file_id": file_id,
        "url": url,
    }


def user_can_access_file(current_user, file_object):
    """检查用户是否有权限访问指定文件"""
    if current_user.role == "system_admin":
        return True
    if current_user.role == "lab_admin":
        return current_user.campus_id == file_object.campus_id
    return current_user.id == file_object.created_by


def save_image_file(current_user, file_storage, campus_id, biz_type, biz_id=None, session=None):
    """
    保存图片文件核心方法
    参数: 当前用户、文件流、校区ID、业务类型、业务ID、数据库会话
    返回: 保存后的 FileObject 实例
    """
    filename, mime_type = _validate_image(file_storage)
    file_bytes = file_storage.read()
    if not file_bytes:
        raise AppError("上传文件不能为空")

    max_size = int(current_app.config.get("MAX_CONTENT_LENGTH", 10 * 1024 * 1024))
    if len(file_bytes) > max_size:
        raise AppError("上传文件过大，请控制在 10MB 以内", 413, 41300)

    digest = hashlib.sha256(file_bytes).hexdigest()
    # 优先用 SeaweedFS，失败则回退到本地存储
    storage_result = _save_seaweedfs(file_bytes, filename, campus_id) or _save_local(
        file_bytes, filename, campus_id, biz_type
    )

    active_session = session or db.session

    # 头像、校区封面等一对一场景：复用以 biz_type + biz_id 唯一标识的旧记录
    SINGLE_IMAGE_BIZ_TYPES = {"avatar", "campus_cover", "lab_photo", "asset_photo"}
    if biz_id is not None and biz_type in SINGLE_IMAGE_BIZ_TYPES:
        existing = (
            active_session.query(FileObject)
            .filter_by(biz_type=biz_type, biz_id=biz_id, status="active")
            .first()
        )
        if existing:
            existing.file_id = storage_result["file_id"]
            existing.url = storage_result["url"]
            existing.original_name = filename
            existing.storage_backend = storage_result["storage_backend"]
            existing.mime_type = mime_type
            existing.size = len(file_bytes)
            existing.sha256 = digest
            existing.created_by = current_user.id
            active_session.flush()
            return existing

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
    # 发布异步事件通知
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
    """根据实验室ID推断所属校区"""
    active_session = session or db.session
    lab = active_session.query(Laboratory).get(int(lab_id))
    if not lab:
        raise AppError("实验室不存在", 404, 40401)
    return lab, lab.campus_id
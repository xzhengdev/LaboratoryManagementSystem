"""
实验室管理蓝图 (lab_bp)
功能：实验室的增删改查、排期查询、照片上传等
权限：普通用户可查看，实验室管理员/系统管理员可增删改
"""

from datetime import datetime  # 日期时间处理
import json                     # JSON 序列化/反序列化
import os                       # 操作系统接口，用于路径处理
import imghdr                   # 图片类型检测模块（通过文件头识别真实格式）
from uuid import uuid4          # 生成唯一标识符，用于文件名

from flask import Blueprint, request, current_app  # Flask核心：蓝图、请求对象、应用上下文
from flask_jwt_extended import jwt_required        # JWT装饰器：要求请求携带有效令牌
from sqlalchemy.exc import IntegrityError          # 数据库完整性错误（如外键约束）
from werkzeug.utils import secure_filename          # 文件名安全化工具（移除危险字符）

from app.extensions import db                       # 数据库实例
from app.models import Approval, Equipment, Laboratory, Reservation  # 数据模型
from app.services.reservation_service import get_lab_schedule  # 排期服务
from app.utils.decorators import get_current_user, role_required  # 用户获取、角色权限
from app.utils.exceptions import AppError           # 自定义异常类
from app.utils.response import success              # 统一成功响应格式
from app.utils.validators import parse_date, parse_time, require_fields  # 参数验证

# ==================== 蓝图创建 ====================
lab_bp = Blueprint("labs", __name__)

# ==================== 图片上传配置 ====================
# 允许上传的图片扩展名集合
ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}

# MIME类型 → 文件扩展名映射
MIMETYPE_EXT_MAP = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}

# imghdr 检测结果 → 文件扩展名映射（统一 jpeg 为 jpg）
IMGHDR_EXT_MAP = {
    "jpeg": "jpg",
    "png": "png",
    "webp": "webp",
}


# ==================== 辅助函数 ====================
def _reservation_can_cleanup(item, now):
    """
    判断预约记录是否可以被清理（删除实验室时的前置检查）
    
    可清理的条件：
    1) 预约状态为已取消(cancelled)或已驳回(rejected)
    2) 预约结束时间已经过了当前时间
    
    参数：
        item - 预约对象
        now  - 当前时间
    
    返回：
        True  - 可以清理
        False - 不可清理（还在进行中或未来）
    """
    # 已取消或已驳回的预约，无论时间都可以清理
    if item.status in {"cancelled", "rejected"}:
        return True
    # 计算预约的结束时间（日期 + 结束时间）
    end_at = datetime.combine(item.reservation_date, item.end_time)
    # 已经过了结束时间的预约可以清理
    return end_at <= now


def _normalize_photos(value):
    """
    规范化实验室照片列表
    
    功能：将前端传来的照片数组统一存储为 JSON 字符串
    支持两种输入格式：
        1) 数组：["url1", "url2"]
        2) JSON字符串：'["url1", "url2"]'
    
    参数：
        value - 原始照片数据（可能为 None、数组、JSON字符串）
    
    返回：
        规范化后的 JSON 字符串
    
    异常：
        AppError - 格式错误或超过限制时抛出
    """
    # 处理空值
    if value in (None, ""):
        return "[]"
    
    data = value
    # 如果是字符串，尝试解析为 JSON
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return "[]"
        try:
            data = json.loads(text)
        except Exception:
            raise AppError("photos 必须是数组或合法 JSON 字符串", 400, 40041)
    
    # 验证是否为数组
    if not isinstance(data, list):
        raise AppError("photos 必须是数组", 400, 40042)

    # 清理和验证每个 URL
    cleaned = []
    for item in data:
        if item in (None, ""):
            continue  # 跳过空值
        url = str(item).strip()
        if not url:
            continue
        # 检查单个 URL 长度限制（500字符）
        if len(url) > 500:
            raise AppError("单张实验室照片地址长度不能超过 500", 400, 40043)
        cleaned.append(url)

    # 检查照片总数限制（最多20张）
    if len(cleaned) > 20:
        raise AppError("实验室照片最多支持 20 张", 400, 40044)
    
    # 返回 JSON 字符串，ensure_ascii=False 保留中文
    return json.dumps(cleaned, ensure_ascii=False)


# ==================== 获取实验室列表 ====================
@lab_bp.get("/labs")
@jwt_required()  # 需要JWT认证
def list_labs():
    """
    获取实验室列表，支持筛选
    
    查询参数：
        campus_id - 校区ID（可选）
        status    - 实验室状态（可选，如 active）
    
    返回：
        实验室信息数组
    """
    # 按 ID 升序查询
    query = Laboratory.query.order_by(Laboratory.id.asc())
    
    # 按校区筛选
    if request.args.get("campus_id"):
        query = query.filter_by(campus_id=int(request.args["campus_id"]))
    
    # 按状态筛选
    if request.args.get("status"):
        query = query.filter_by(status=request.args["status"])
    
    return success([item.to_dict() for item in query.all()])


# ==================== 获取实验室详情 ====================
@lab_bp.get("/labs/<int:lab_id>")
@jwt_required()
def lab_detail(lab_id):
    """
    获取实验室详情，包含关联的设备清单
    
    参数：
        lab_id - 实验室ID
    
    返回：
        实验室详情字典，包含 equipment 字段
    """
    item = Laboratory.query.get_or_404(lab_id)
    # to_dict 时额外传入 equipment 列表
    return success(item.to_dict({"equipment": [eq.to_dict() for eq in item.equipment]}))


# ==================== 获取实验室排期 ====================
@lab_bp.get("/labs/<int:lab_id>/schedule")
@jwt_required()
def lab_schedule(lab_id):
    """
    查询实验室某一天的排期（预约时间表）
    这是预约页面和 AI 助手的核心接口
    
    参数：
        lab_id - 实验室ID（URL路径）
    
    查询参数：
        date - 日期（必填，格式如 2024-01-15）
    
    返回：
        该实验室在指定日期的可用时间段
    """
    item = Laboratory.query.get_or_404(lab_id)
    date_str = request.args.get("date")
    if not date_str:
        raise AppError("请传入 date 参数")
    return success(get_lab_schedule(item, parse_date(date_str, "date")))


# ==================== 创建实验室 ====================
@lab_bp.post("/labs")
@role_required("lab_admin", "system_admin")  # 需要实验室管理员或系统管理员
def create_lab():
    """
    创建新实验室
    
    权限规则：
        - 系统管理员：可操作全部校区
        - 实验室管理员：只能操作自己所属校区
    
    请求体必填字段：
        campus_id, lab_name, location, capacity, open_time, close_time
    
    请求体可选字段：
        status, description, photos
    """
    current_user = get_current_user()
    payload = request.get_json(silent=True) or {}
    
    # 验证必填字段
    require_fields(
        payload,
        ["campus_id", "lab_name", "location", "capacity", "open_time", "close_time"],
    )
    
    campus_id = int(payload["campus_id"])
    
    # 权限检查：实验室管理员只能管理本校区
    if current_user.role == "lab_admin" and current_user.campus_id != campus_id:
        raise AppError("只能管理本校区实验室", 403, 40310)
    
    # 创建实验室实例
    item = Laboratory(
        campus_id=campus_id,
        lab_name=payload["lab_name"],
        location=payload["location"],
        capacity=int(payload["capacity"]),
        open_time=parse_time(payload["open_time"], "open_time"),   # 解析时间格式
        close_time=parse_time(payload["close_time"], "close_time"),
        status=payload.get("status", "active"),
        description=payload.get("description", ""),
        photos=_normalize_photos(payload.get("photos")),
    )
    
    db.session.add(item)
    db.session.commit()
    return success(item.to_dict(), "创建实验室成功")


# ==================== 更新实验室 ====================
@lab_bp.put("/labs/<int:lab_id>")
@role_required("lab_admin", "system_admin")
def update_lab(lab_id):
    """
    更新实验室信息
    
    权限规则：同创建接口
        - 实验室管理员只能更新本校区实验室
        - 系统管理员可更新任意实验室
    """
    current_user = get_current_user()
    payload = request.get_json(silent=True) or {}
    item = Laboratory.query.get_or_404(lab_id)
    
    # 权限检查：实验室管理员只能更新本校区实验室
    if current_user.role == "lab_admin" and current_user.campus_id != item.campus_id:
        raise AppError("只能更新本校区实验室", 403, 40311)

    # 批量更新普通字段
    for field in ["lab_name", "location", "status", "description"]:
        if field in payload:
            setattr(item, field, payload[field])
    
    # 更新照片（需要规范化处理）
    if "photos" in payload:
        item.photos = _normalize_photos(payload.get("photos"))
    
    # 更新校区（额外权限检查）
    if "campus_id" in payload:
        campus_id = int(payload["campus_id"])
        if current_user.role == "lab_admin" and current_user.campus_id != campus_id:
            raise AppError("不能把实验室转移到其他校区", 403, 40312)
        item.campus_id = campus_id
    
    # 更新容量
    if "capacity" in payload:
        item.capacity = int(payload["capacity"])
    
    # 更新时间段
    if "open_time" in payload:
        item.open_time = parse_time(payload["open_time"], "open_time")
    if "close_time" in payload:
        item.close_time = parse_time(payload["close_time"], "close_time")
    
    db.session.commit()
    return success(item.to_dict(), "更新实验室成功")


# ==================== 上传实验室照片 ====================
@lab_bp.post("/labs/upload-photo")
@role_required("lab_admin", "system_admin")
def upload_lab_photo():
    """
    上传实验室照片（仅管理员可用）
    
    请求：multipart/form-data，字段名 'file'
    支持格式：jpg, jpeg, png, webp
    
    返回：
        {
            "url": "完整访问URL",
            "path": "相对路径"
        }
    
    注意：上传成功后需调用更新接口将 URL 加入 photos 数组
    """
    # ----- 1. 验证文件是否存在 -----
    if "file" not in request.files:
        raise AppError("请上传实验室封面文件", 400, 40071)

    file = request.files["file"]
    if not file or not file.filename:
        raise AppError("实验室封面文件无效", 400, 40072)

    # ----- 2. 安全化文件名并提取扩展名 -----
    filename = secure_filename(file.filename)
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    mime = (file.mimetype or "").lower()

    # ----- 3. 尝试多种方式确定文件类型 -----
    # 方式1：MIME类型映射
    if not ext:
        ext = MIMETYPE_EXT_MAP.get(mime, "")
    
    # 方式2：从MIME字符串提取
    if not ext and mime.startswith("image/"):
        sub = mime.split("/", 1)[1].split(";", 1)[0].strip()
        if sub == "jpeg":
            sub = "jpg"
        ext = sub
    
    # 方式3：文件头识别（最可靠）
    if not ext:
        detected = imghdr.what(file.stream)
        if detected:
            ext = IMGHDR_EXT_MAP.get(detected, detected)
        file.stream.seek(0)
    
    # ----- 4. 验证扩展名 -----
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise AppError("仅支持 jpg/jpeg/png/webp 格式", 400, 40073)

    # ----- 5. 保存文件 -----
    save_name = f"{uuid4().hex}.{ext}"
    relative_path = os.path.join("labs", save_name)  # labs/xxx.jpg
    absolute_path = os.path.join(current_app.config["UPLOAD_ROOT"], relative_path)
    file.save(absolute_path)

    # ----- 6. 返回访问URL -----
    public_path = f"/uploads/{relative_path.replace(os.sep, '/')}"
    public_url = f"{request.host_url.rstrip('/')}{public_path}"
    return success({"url": public_url, "path": public_path}, "实验室封面上传成功")


# ==================== 删除实验室 ====================
@lab_bp.delete("/labs/<int:lab_id>")
@role_required("lab_admin", "system_admin")
def delete_lab(lab_id):
    """
    删除实验室（级联删除关联数据）
    
    删除流程：
        1. 检查权限
        2. 检查是否有未结束的预约（阻止删除）
        3. 删除审批记录 → 删除预约 → 删除设备 → 删除实验室
    
    注意事项：
        - 只有已结束或已取消的预约才允许删除
        - 使用事务保证数据一致性
    """
    current_user = get_current_user()
    item = Laboratory.query.get_or_404(lab_id)
    
    # 权限检查：实验室管理员只能删除本校区实验室
    if current_user.role == "lab_admin" and current_user.campus_id != item.campus_id:
        raise AppError("只能删除本校区实验室", 403, 40313)

    # ----- 1. 检查是否有未结束的预约 -----
    reservations = Reservation.query.filter_by(lab_id=item.id).all()
    now = datetime.now()
    # 筛选出不可清理的预约（正在进行中或未来的）
    blocking = [r for r in reservations if not _reservation_can_cleanup(r, now)]
    if blocking:
        raise AppError(
            f"该实验室下仍有 {len(blocking)} 条未结束预约，无法删除",
            400,
            40031,
        )

    # ----- 2. 按依赖顺序删除关联数据 -----
    # 顺序：审批记录 → 预约 → 设备 → 实验室
    
    # 删除所有预约关联的审批记录
    for reservation in reservations:
        Approval.query.filter_by(reservation_id=reservation.id).delete(
            synchronize_session=False  # 不自动同步会话，提升性能
        )
        db.session.delete(reservation)

    # 删除实验室下的所有设备
    equipment_items = Equipment.query.filter_by(lab_id=item.id).all()
    for equipment in equipment_items:
        db.session.delete(equipment)

    # 删除实验室本身
    db.session.delete(item)
    
    # ----- 3. 提交事务，处理完整性错误 -----
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise AppError("该实验室存在关联数据，无法删除", 400, 40032)
    
    return success(message="删除实验室成功")
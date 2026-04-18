"""
校区管理蓝图 (campus_bp)
功能：校区的增删改查、封面上传等
权限：普通用户可查看，系统管理员才能增删改
"""
import os              # 操作系统接口，用于路径处理
import imghdr          # 图片类型检测模块（通过文件头识别真实格式）
from uuid import uuid4  # 生成唯一标识符，用于文件名
from flask import Blueprint, current_app, request  # Flask核心：蓝图、应用上下文、请求对象
from flask_jwt_extended import jwt_required        # JWT装饰器：要求请求携带有效令牌
from werkzeug.utils import secure_filename          # 文件名安全化工具（移除危险字符）

from app.extensions import db                       # 数据库实例
from app.models import Campus                       # 校区数据模型
from app.utils.decorators import role_required      # 角色权限装饰器（要求指定角色）
from app.utils.exceptions import AppError           # 自定义异常类
from app.utils.response import success              # 统一成功响应格式
from app.utils.validators import require_fields     # 验证必填字段

# ==================== 蓝图创建 ====================
campus_bp = Blueprint('campuses', __name__)
# ==================== 图片上传配置 ====================
# 允许上传的图片扩展名集合
ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
# MIME类型 → 文件扩展名映射
MIMETYPE_EXT_MAP = {
    'image/jpeg': 'jpg',
    'image/jpg': 'jpg',
    'image/png': 'png',
    'image/webp': 'webp'
}

# imghdr 检测结果 → 文件扩展名映射（统一 jpeg 为 jpg）
IMGHDR_EXT_MAP = {
    'jpeg': 'jpg',
    'png': 'png',
    'webp': 'webp'
}


# ==================== 辅助函数 ====================
def _normalize_cover_url(value):
    """
    规范化封面URL
    功能：验证并处理封面地址，空值转为None，检查长度限制
    
    参数：
        value - 原始URL值（可能为 None、空字符串、或URL字符串）
    
    返回：
        处理后的URL字符串或None
    
    异常：
        AppError - URL长度超过500字符时抛出
    """
    # 处理空值
    if value in (None, ''):
        return None
    # 转为字符串并去除首尾空格
    cover_url = str(value).strip()
    if not cover_url:
        return None
    # 检查长度限制（500字符）
    if len(cover_url) > 500:
        raise AppError('封面地址长度不能超过 500', 400, 40021)
    return cover_url


# ==================== 获取校区列表 ====================
@campus_bp.get('/campuses')
@jwt_required()  # 需要JWT认证（登录用户即可访问）
def list_campuses():
    """
    获取所有校区列表
    返回：按ID升序排列的校区信息数组
    """
    # 查询所有校区，按ID升序排序
    items = Campus.query.order_by(Campus.id.asc()).all()
    # 将每个校区模型转换为字典并返回
    return success([item.to_dict() for item in items])


# ==================== 获取单个校区详情 ====================
@campus_bp.get('/campuses/<int:campus_id>')
@jwt_required()  # 需要JWT认证
def campus_detail(campus_id):
    """
    获取指定校区的详细信息
    
    参数：
        campus_id - 校区ID（URL路径参数）
    
    返回：
        校区信息字典
    """
    # query.get_or_404: 根据ID查询，不存在时自动返回404错误
    return success(Campus.query.get_or_404(campus_id).to_dict())


# ==================== 创建校区 ====================
@campus_bp.post('/campuses')
@role_required('system_admin')  # 需要 system_admin 角色才能访问
def create_campus():
    """
    创建新校区（仅系统管理员可用）
    
    请求体：
        {
            "campus_name": "校区名称",  // 必填
            "address": "详细地址",      // 必填
            "description": "描述",      // 可选
            "cover_url": "封面URL",     // 可选
            "status": "active"         // 可选，默认 active
        }
    
    返回：
        新创建的校区信息
    """
    # 获取请求JSON，解析失败时返回空字典
    payload = request.get_json(silent=True) or {}
    # 验证必填字段：campus_name 和 address
    require_fields(payload, ['campus_name', 'address'])
    # 创建校区模型实例
    item = Campus(
        campus_name=payload['campus_name'],           # 校区名称
        address=payload['address'],                   # 地址
        description=payload.get('description', ''),   # 描述（默认为空字符串）
        cover_url=_normalize_cover_url(payload.get('cover_url')),  # 封面URL（规范化处理）
        status=payload.get('status', 'active')        # 状态（默认为 active）
    )
    # 保存到数据库
    db.session.add(item)
    db.session.commit()
    return success(item.to_dict(), '创建校区成功')


# ==================== 更新校区 ====================
@campus_bp.put('/campuses/<int:campus_id>')
@role_required('system_admin')  # 需要 system_admin 角色
def update_campus(campus_id):
    """
    更新校区信息（仅系统管理员可用）
    参数：
        campus_id - 校区ID（URL路径参数）
    请求体：
        可选字段：campus_name, address, description, status, cover_url
    返回：
        更新后的校区信息
    """
    # 获取请求数据
    payload = request.get_json(silent=True) or {}
    # 查询校区，不存在则404
    item = Campus.query.get_or_404(campus_id)

    # 批量更新普通字段（字符串/状态字段）
    for field in ['campus_name', 'address', 'description', 'status']:
        if field in payload:
            setattr(item, field, payload[field])  # 动态设置属性值

    # 单独处理封面URL（需要规范化处理）
    if 'cover_url' in payload:
        item.cover_url = _normalize_cover_url(payload.get('cover_url'))

    # 提交更改
    db.session.commit()
    return success(item.to_dict(), '更新校区成功')


# ==================== 上传校区封面 ====================
@campus_bp.post('/campuses/upload-cover')
@role_required('system_admin')  # 需要 system_admin 角色
def upload_campus_cover():
    """
    上传校区封面图片（仅系统管理员可用）
    
    请求：multipart/form-data，字段名 'file'
    支持格式：jpg, jpeg, png, webp
    
    返回：
        {
            "url": "完整访问URL",
            "path": "相对路径"
        }
    """
    # ----- 1. 验证文件是否存在 -----
    if 'file' not in request.files:
        raise AppError('请上传校区封面文件', 400, 40022)

    file = request.files['file']
    if not file or not file.filename:
        raise AppError('校区封面文件无效', 400, 40023)

    # ----- 2. 安全化文件名并提取扩展名 -----
    filename = secure_filename(file.filename)  # 移除危险字符
    # 从文件名中提取扩展名（如 'cover.jpg' → 'jpg'）
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    # 获取MIME类型（如 'image/png'）
    mime = (file.mimetype or '').lower()

    # ----- 3. 尝试多种方式确定文件类型 -----
    # 方式1：如果扩展名为空，通过MIME类型映射
    if not ext:
        ext = MIMETYPE_EXT_MAP.get(mime, '')
    
    # 方式2：如果仍然没有，从MIME字符串中提取（如 'image/jpeg' → 'jpg'）
    if not ext and mime.startswith('image/'):
        sub = mime.split('/', 1)[1].split(';', 1)[0].strip()
        if sub == 'jpeg':
            sub = 'jpg'
        ext = sub
    
    # 方式3：最后使用 imghdr 读取文件头识别真实类型（防止伪造扩展名）
    if not ext:
        detected = imghdr.what(file.stream)  # 读取文件头识别
        if detected:
            ext = IMGHDR_EXT_MAP.get(detected, detected)
        file.stream.seek(0)  # 重置文件指针，以便后续保存

    # ----- 4. 验证扩展名是否允许 -----
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise AppError('仅支持 jpg/jpeg/png/webp 格式', 400, 40024)

    # ----- 5. 生成唯一文件名并保存 -----
    save_name = f'{uuid4().hex}.{ext}'  # 如 'a1b2c3d4e5f6.jpg'
    relative_path = os.path.join('campuses', save_name)  # 相对路径：campuses/xxx.jpg
    upload_root = current_app.config['UPLOAD_ROOT']      # 上传根目录配置
    absolute_path = os.path.join(upload_root, relative_path)  # 绝对路径
    file.save(absolute_path)  # 保存文件到服务器

    # ----- 6. 生成访问URL并返回 -----
    # 将系统路径分隔符转换为URL使用的正斜杠
    public_path = f"/uploads/{relative_path.replace(os.sep, '/')}"
    # 生成完整URL（如 http://localhost:5000/uploads/campuses/xxx.jpg）
    public_url = f"{request.host_url.rstrip('/')}{public_path}"
    
    return success({'url': public_url, 'path': public_path}, '校区封面上传成功')


# ==================== 删除校区 ====================
@campus_bp.delete('/campuses/<int:campus_id>')
@role_required('system_admin')  # 需要 system_admin 角色
def delete_campus(campus_id):
    """
    删除校区（仅系统管理员可用）
    
    注意：删除校区可能会影响关联的实验室等数据
    实际项目中可能需要考虑软删除或检查关联数据
    
    参数：
        campus_id - 校区ID（URL路径参数）
    """
    # 查询校区（不存在时返回自定义错误，而非404页面）
    item = Campus.query.get(campus_id)
    if not item:
        raise AppError('校区不存在', 404, 40401)
    
    # 删除校区
    db.session.delete(item)
    db.session.commit()
    
    return success(message='删除校区成功')
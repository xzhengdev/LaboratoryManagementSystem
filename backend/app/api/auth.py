"""
认证与用户管理蓝图 (auth_bp)
功能：用户登录、个人信息管理、头像上传等
"""
import imghdr          # 图片类型检测模块（通过文件头识别真实格式）
import os              # 操作系统接口，用于路径处理
from uuid import uuid4  # 生成唯一标识符，用于文件名
from flask import Blueprint, current_app, request  # Flask核心：蓝图、应用上下文、请求对象
from flask_jwt_extended import jwt_required        # JWT装饰器：要求请求携带有效令牌
from werkzeug.utils import secure_filename          # 文件名安全化工具（移除危险字符）
from app.extensions import db                       # 数据库实例
from app.services.auth_service import login         # 认证服务：处理登录逻辑
from app.utils.decorators import get_current_user   # 获取当前登录用户
from app.utils.exceptions import AppError           # 自定义异常类
from app.utils.response import success              # 统一成功响应格式
from app.utils.validators import require_fields     # 验证必填字段
# ==================== 蓝图创建 ====================
auth_bp = Blueprint('auth', __name__)
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

# ==================== 登录接口 ====================
@auth_bp.post('/auth/login')
def login_api():
    """
    用户登录
    请求体：{"username": "用户名", "password": "密码", "role": "可选角色"}
    返回：JWT令牌和用户信息
    """
    # 获取请求JSON，解析失败时返回空字典
    payload = request.get_json(silent=True) or {}
    # 验证必填字段：username 和 password
    require_fields(payload, ['username', 'password'])
    # 调用登录服务，返回结果包装为成功响应
    return success(
        login(payload['username'], payload['password'], payload.get('role')),
        '登录成功'
    )


# ==================== 获取个人信息 ====================
@auth_bp.get('/auth/profile')
@jwt_required()  # 需要JWT认证
def profile_api():
    """
    获取当前登录用户的个人信息
    返回：用户信息字典
    """
    return success(get_current_user().to_dict())


# ==================== 更新个人信息 ====================
@auth_bp.put('/auth/profile')
@jwt_required()  # 需要JWT认证
def update_profile_api():
    """
    更新当前登录用户的个人信息
    请求体：可选字段 real_name, email, phone, avatar_url
    """
    # 获取请求数据
    payload = request.get_json(silent=True) or {}
    # 获取当前登录用户
    user = get_current_user()
    # ----- 更新真实姓名 -----
    if 'real_name' in payload:
        real_name = str(payload.get('real_name') or '').strip()
        if not real_name:  # 真实姓名不能为空
            raise AppError('姓名不能为空', 400, 40061)
        user.real_name = real_name
    # ----- 更新邮箱 -----
    if 'email' in payload:
        email = str(payload.get('email') or '').strip()
        user.email = email or None  # 空字符串转为 None
    # ----- 更新手机号 -----
    if 'phone' in payload:
        phone = str(payload.get('phone') or '').strip()
        user.phone = phone or None
    # ----- 更新头像URL -----
    if 'avatar_url' in payload:
        avatar_url = str(payload.get('avatar_url') or '').strip()
        if avatar_url and len(avatar_url) > 500:  # URL长度限制
            raise AppError('头像地址长度不能超过 500', 400, 40062)
        user.avatar_url = avatar_url or None
    # 提交数据库更改
    db.session.commit()
    return success(user.to_dict(), '资料更新成功')


# ==================== 上传头像（文件上传）====================
@auth_bp.post('/auth/upload-avatar')
@jwt_required()  # 需要JWT认证
def upload_avatar_api():
    """
    上传头像图片文件
    请求：multipart/form-data，字段名 'file'
    返回：图片的访问URL
    """
    # ----- 1. 验证文件是否存在 -----
    if 'file' not in request.files:
        raise AppError('请上传头像文件', 400, 40063)
    file = request.files['file']
    if not file or not file.filename:
        raise AppError('头像文件无效', 400, 40064)
    # ----- 2. 安全化文件名并提取扩展名 -----
    filename = secure_filename(file.filename)  # 移除 ../ 等危险字符
    # 从文件名中提取扩展名（如 'avatar.jpg' → 'jpg'）
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
        raise AppError('仅支持 jpg/jpeg/png/webp 格式', 400, 40065)
    # ----- 5. 生成唯一文件名并保存 -----
    save_name = f'{uuid4().hex}.{ext}'  # 如 'a1b2c3d4e5f6.jpg'
    relative_path = os.path.join('avatars', save_name)  # 相对路径：avatars/xxx.jpg
    upload_root = current_app.config['UPLOAD_ROOT']     # 上传根目录配置
    absolute_path = os.path.join(upload_root, relative_path)  # 绝对路径
    file.save(absolute_path)  # 保存文件到服务器
    # ----- 6. 生成访问URL并返回 -----
    # 将系统路径分隔符转换为URL使用的正斜杠
    public_path = f"/uploads/{relative_path.replace(os.sep, '/')}"
    # 生成完整URL（如 http://localhost:5000/uploads/avatars/xxx.jpg）
    public_url = f"{request.host_url.rstrip('/')}{public_path}"
    return success({'url': public_url, 'path': public_path}, '头像上传成功')
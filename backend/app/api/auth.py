"""
认证与用户管理蓝图 (auth_bp)
功能：用户登录、个人信息管理、头像上传等
"""
from flask import Blueprint, request  # Flask核心：蓝图、请求对象
from flask_jwt_extended import jwt_required        # JWT装饰器：要求请求携带有效令牌
from app.extensions import db                       # 数据库实例
from app.models import User
from app.services.auth_service import login         # 认证服务：处理登录逻辑
from app.services.db_router_service import campus_db_session
from app.services.file_storage_service import save_image_file
from app.utils.decorators import get_current_user   # 获取当前登录用户
from app.utils.exceptions import AppError           # 自定义异常类
from app.utils.response import success              # 统一成功响应格式
from app.utils.validators import require_fields     # 验证必填字段
# ==================== 蓝图创建 ====================
auth_bp = Blueprint('auth', __name__)
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


# ==================== 修改密码 ====================
@auth_bp.post('/auth/change-password')
@jwt_required()  # 需要JWT认证
def change_password_api():
    """
    修改当前登录用户密码
    请求体：{"old_password": "旧密码", "new_password": "新密码"}
    """
    payload = request.get_json(silent=True) or {}
    require_fields(payload, ['old_password', 'new_password'])

    old_password = str(payload.get('old_password') or '')
    new_password = str(payload.get('new_password') or '')
    confirm_password = str(payload.get('confirm_password') or new_password)

    if len(new_password) < 6:
        raise AppError('新密码至少 6 位', 400, 40066)
    if new_password != confirm_password:
        raise AppError('两次输入的新密码不一致', 400, 40067)

    user = get_current_user()
    if not user.check_password(old_password):
        raise AppError('原密码不正确', 400, 40068)
    if user.check_password(new_password):
        raise AppError('新密码不能与原密码相同', 400, 40069)

    user.set_password(new_password)
    db.session.commit()
    return success({'user_id': user.id}, '密码修改成功')


# ==================== 上传头像（文件上传）====================
@auth_bp.post('/auth/upload-avatar')
@jwt_required()  # 需要JWT认证
def upload_avatar_api():
    """
    上传头像图片文件
    请求：multipart/form-data，字段名 'file'
    返回：图片的访问URL
    """
    current_user = get_current_user()
    file_storage = request.files.get('file')
    if not file_storage:
        raise AppError('请上传头像文件', 400, 40063)

    campus_id = current_user.campus_id
    if not campus_id:
        raise AppError('当前账号未绑定校区，无法上传头像', 400, 40070)

    with campus_db_session(campus_id) as session:
        file_obj = save_image_file(
            current_user=current_user,
            file_storage=file_storage,
            campus_id=campus_id,
            biz_type='avatar',
            biz_id=current_user.id,
            session=session,
        )
        response_data = file_obj.to_dict()
        file_url = file_obj.url
        shard_user = session.query(User).get(int(current_user.id))
        if shard_user:
            shard_user.avatar_url = file_url
        session.commit()

    user = get_current_user()
    user.avatar_url = file_url
    db.session.commit()
    return success(response_data, '头像上传成功')

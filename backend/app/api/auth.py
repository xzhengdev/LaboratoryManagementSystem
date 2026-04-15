import imghdr
import os
from uuid import uuid4

from flask import Blueprint, current_app, request
from flask_jwt_extended import jwt_required
from werkzeug.utils import secure_filename

from app.extensions import db
from app.services.auth_service import login
from app.utils.decorators import get_current_user
from app.utils.exceptions import AppError
from app.utils.response import success
from app.utils.validators import require_fields


auth_bp = Blueprint('auth', __name__)
ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}
MIMETYPE_EXT_MAP = {
    'image/jpeg': 'jpg',
    'image/jpg': 'jpg',
    'image/png': 'png',
    'image/webp': 'webp'
}
IMGHDR_EXT_MAP = {
    'jpeg': 'jpg',
    'png': 'png',
    'webp': 'webp'
}


@auth_bp.post('/auth/login')
def login_api():
    payload = request.get_json(silent=True) or {}
    require_fields(payload, ['username', 'password'])
    return success(login(payload['username'], payload['password'], payload.get('role')), '登录成功')


@auth_bp.get('/auth/profile')
@jwt_required()
def profile_api():
    return success(get_current_user().to_dict())


@auth_bp.put('/auth/profile')
@jwt_required()
def update_profile_api():
    payload = request.get_json(silent=True) or {}
    user = get_current_user()

    if 'real_name' in payload:
        real_name = str(payload.get('real_name') or '').strip()
        if not real_name:
            raise AppError('姓名不能为空', 400, 40061)
        user.real_name = real_name

    if 'email' in payload:
        email = str(payload.get('email') or '').strip()
        user.email = email or None

    if 'phone' in payload:
        phone = str(payload.get('phone') or '').strip()
        user.phone = phone or None

    if 'avatar_url' in payload:
        avatar_url = str(payload.get('avatar_url') or '').strip()
        if avatar_url and len(avatar_url) > 500:
            raise AppError('头像地址长度不能超过 500', 400, 40062)
        user.avatar_url = avatar_url or None

    db.session.commit()
    return success(user.to_dict(), '资料更新成功')


@auth_bp.post('/auth/upload-avatar')
@jwt_required()
def upload_avatar_api():
    if 'file' not in request.files:
        raise AppError('请上传头像文件', 400, 40063)

    file = request.files['file']
    if not file or not file.filename:
        raise AppError('头像文件无效', 400, 40064)

    filename = secure_filename(file.filename)
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    mime = (file.mimetype or '').lower()

    if not ext:
        ext = MIMETYPE_EXT_MAP.get(mime, '')

    if not ext and mime.startswith('image/'):
        sub = mime.split('/', 1)[1].split(';', 1)[0].strip()
        if sub == 'jpeg':
            sub = 'jpg'
        ext = sub

    if not ext:
        detected = imghdr.what(file.stream)
        if detected:
            ext = IMGHDR_EXT_MAP.get(detected, detected)
        file.stream.seek(0)

    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise AppError('仅支持 jpg/jpeg/png/webp 格式', 400, 40065)

    save_name = f'{uuid4().hex}.{ext}'
    relative_path = os.path.join('avatars', save_name)
    upload_root = current_app.config['UPLOAD_ROOT']
    absolute_path = os.path.join(upload_root, relative_path)
    file.save(absolute_path)

    public_path = f"/uploads/{relative_path.replace(os.sep, '/')}"
    public_url = f"{request.host_url.rstrip('/')}{public_path}"
    return success({'url': public_url, 'path': public_path}, '头像上传成功')

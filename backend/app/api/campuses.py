import os
import imghdr
from uuid import uuid4

from flask import Blueprint, current_app, request
from flask_jwt_extended import jwt_required
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import Campus
from app.utils.decorators import role_required
from app.utils.exceptions import AppError
from app.utils.response import success
from app.utils.validators import require_fields


campus_bp = Blueprint('campuses', __name__)
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


def _normalize_cover_url(value):
    if value in (None, ''):
        return None
    cover_url = str(value).strip()
    if not cover_url:
        return None
    if len(cover_url) > 500:
        raise AppError('封面地址长度不能超过 500', 400, 40021)
    return cover_url


@campus_bp.get('/campuses')
@jwt_required()
def list_campuses():
    items = Campus.query.order_by(Campus.id.asc()).all()
    return success([item.to_dict() for item in items])


@campus_bp.get('/campuses/<int:campus_id>')
@jwt_required()
def campus_detail(campus_id):
    return success(Campus.query.get_or_404(campus_id).to_dict())


@campus_bp.post('/campuses')
@role_required('system_admin')
def create_campus():
    payload = request.get_json(silent=True) or {}
    require_fields(payload, ['campus_name', 'address'])
    item = Campus(
        campus_name=payload['campus_name'],
        address=payload['address'],
        description=payload.get('description', ''),
        cover_url=_normalize_cover_url(payload.get('cover_url')),
        status=payload.get('status', 'active')
    )
    db.session.add(item)
    db.session.commit()
    return success(item.to_dict(), '创建校区成功')


@campus_bp.put('/campuses/<int:campus_id>')
@role_required('system_admin')
def update_campus(campus_id):
    payload = request.get_json(silent=True) or {}
    item = Campus.query.get_or_404(campus_id)

    for field in ['campus_name', 'address', 'description', 'status']:
        if field in payload:
            setattr(item, field, payload[field])

    if 'cover_url' in payload:
        item.cover_url = _normalize_cover_url(payload.get('cover_url'))

    db.session.commit()
    return success(item.to_dict(), '更新校区成功')


@campus_bp.post('/campuses/upload-cover')
@role_required('system_admin')
def upload_campus_cover():
    if 'file' not in request.files:
        raise AppError('请上传校区封面文件', 400, 40022)

    file = request.files['file']
    if not file or not file.filename:
        raise AppError('校区封面文件无效', 400, 40023)

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
        raise AppError('仅支持 jpg/jpeg/png/webp 格式', 400, 40024)

    save_name = f'{uuid4().hex}.{ext}'
    relative_path = os.path.join('campuses', save_name)
    absolute_path = os.path.join(current_app.config['UPLOAD_ROOT'], relative_path)
    file.save(absolute_path)

    public_path = f"/uploads/{relative_path.replace(os.sep, '/')}"
    public_url = f"{request.host_url.rstrip('/')}{public_path}"
    return success({'url': public_url, 'path': public_path}, '校区封面上传成功')


@campus_bp.delete('/campuses/<int:campus_id>')
@role_required('system_admin')
def delete_campus(campus_id):
    item = Campus.query.get(campus_id)
    if not item:
        raise AppError('校区不存在', 404, 40401)
    db.session.delete(item)
    db.session.commit()
    return success(message='删除校区成功')

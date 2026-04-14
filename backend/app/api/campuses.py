from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from app.extensions import db
from app.models import Campus
from app.utils.decorators import role_required
from app.utils.exceptions import AppError
from app.utils.response import success
from app.utils.validators import require_fields


campus_bp = Blueprint("campuses", __name__)


@campus_bp.get("/campuses")
@jwt_required()
def list_campuses():
    # 校区列表接口，所有已登录用户都可访问。
    items = Campus.query.order_by(Campus.id.asc()).all()
    return success([item.to_dict() for item in items])


@campus_bp.get("/campuses/<int:campus_id>")
@jwt_required()
def campus_detail(campus_id):
    return success(Campus.query.get_or_404(campus_id).to_dict())


@campus_bp.post("/campuses")
@role_required("system_admin")
def create_campus():
    # 校区新增仅允许系统管理员操作。
    payload = request.get_json(silent=True) or {}
    require_fields(payload, ["campus_name", "address"])
    item = Campus(
        campus_name=payload["campus_name"],
        address=payload["address"],
        description=payload.get("description", ""),
        status=payload.get("status", "active"),
    )
    db.session.add(item)
    db.session.commit()
    return success(item.to_dict(), "创建校区成功")


@campus_bp.put("/campuses/<int:campus_id>")
@role_required("system_admin")
def update_campus(campus_id):
    # 校区更新仅允许系统管理员操作。
    payload = request.get_json(silent=True) or {}
    item = Campus.query.get_or_404(campus_id)
    for field in ["campus_name", "address", "description", "status"]:
        if field in payload:
            setattr(item, field, payload[field])
    db.session.commit()
    return success(item.to_dict(), "更新校区成功")


@campus_bp.delete("/campuses/<int:campus_id>")
@role_required("system_admin")
def delete_campus(campus_id):
    # 校区删除仅允许系统管理员操作。
    item = Campus.query.get(campus_id)
    if not item:
        raise AppError("校区不存在", 404, 40401)
    db.session.delete(item)
    db.session.commit()
    return success(message="删除校区成功")

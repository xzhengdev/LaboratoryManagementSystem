from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from app.extensions import db
from app.models import Equipment, Laboratory
from app.utils.decorators import get_current_user, role_required
from app.utils.exceptions import AppError
from app.utils.response import success
from app.utils.validators import require_fields


equipment_bp = Blueprint("equipment", __name__)


@equipment_bp.get("/equipment")
@jwt_required()
def list_equipment():
    # 设备列表接口，支持按实验室过滤。
    query = Equipment.query.order_by(Equipment.id.asc())
    if request.args.get("lab_id"):
        query = query.filter_by(lab_id=int(request.args["lab_id"]))
    return success([item.to_dict() for item in query.all()])


@equipment_bp.post("/equipment")
@role_required("lab_admin", "system_admin")
def create_equipment():
    # 创建设备时，实验室管理员只能操作自己校区的实验室。
    current_user = get_current_user()
    payload = request.get_json(silent=True) or {}
    require_fields(payload, ["lab_id", "equipment_name", "quantity"])
    lab = Laboratory.query.get_or_404(int(payload["lab_id"]))
    if current_user.role == "lab_admin" and current_user.campus_id != lab.campus_id:
        raise AppError("只能管理本校区实验室设备", 403, 40314)
    item = Equipment(
        lab_id=lab.id,
        equipment_name=payload["equipment_name"],
        quantity=int(payload["quantity"]),
        status=payload.get("status", "active"),
        description=payload.get("description", ""),
    )
    db.session.add(item)
    db.session.commit()
    return success(item.to_dict(), "创建设备成功")


@equipment_bp.put("/equipment/<int:equipment_id>")
@role_required("lab_admin", "system_admin")
def update_equipment(equipment_id):
    # 设备更新接口。
    current_user = get_current_user()
    payload = request.get_json(silent=True) or {}
    item = Equipment.query.get_or_404(equipment_id)
    if current_user.role == "lab_admin" and current_user.campus_id != item.lab.campus_id:
        raise AppError("只能管理本校区实验室设备", 403, 40315)
    for field in ["equipment_name", "status", "description"]:
        if field in payload:
            setattr(item, field, payload[field])
    if "quantity" in payload:
        item.quantity = int(payload["quantity"])
    db.session.commit()
    return success(item.to_dict(), "更新设备成功")


@equipment_bp.delete("/equipment/<int:equipment_id>")
@role_required("lab_admin", "system_admin")
def delete_equipment(equipment_id):
    # 设备删除接口。
    current_user = get_current_user()
    item = Equipment.query.get_or_404(equipment_id)
    if current_user.role == "lab_admin" and current_user.campus_id != item.lab.campus_id:
        raise AppError("只能管理本校区实验室设备", 403, 40316)
    db.session.delete(item)
    db.session.commit()
    return success(message="删除设备成功")

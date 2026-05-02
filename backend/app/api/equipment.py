from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from app.models import Equipment, Laboratory
from app.services.db_router_service import (
    campus_db_session,
    find_across_campuses,
    aggregate_across_campuses,
)
from app.utils.decorators import get_current_user, role_required
from app.utils.exceptions import AppError
from app.utils.response import success
from app.utils.validators import require_fields


equipment_bp = Blueprint("equipment", __name__)


@equipment_bp.get("/equipment")
@jwt_required()
def list_equipment():
    lab_id_str = request.args.get("lab_id")
    if lab_id_str:
        lab_id = int(lab_id_str)
        lab, campus_id = find_across_campuses(Laboratory, lab_id)
        if not lab:
            raise AppError("lab not found", 404, 40401)
        with campus_db_session(campus_id) as session:
            items = session.query(Equipment).filter_by(lab_id=lab_id).order_by(Equipment.id.asc()).all()
            result = [item.to_dict() for item in items]
    else:
        def _query(session):
            items = session.query(Equipment).order_by(Equipment.id.asc()).all()
            return [item.to_dict() for item in items]
        result = aggregate_across_campuses(Equipment, _query)
    return success(result)


@equipment_bp.post("/equipment")
@role_required("lab_admin", "system_admin")
def create_equipment():
    current_user = get_current_user()
    payload = request.get_json(silent=True) or {}
    require_fields(payload, ["lab_id", "equipment_name", "quantity"])
    lab, campus_id = find_across_campuses(Laboratory, int(payload["lab_id"]))
    if not lab:
        raise AppError("lab not found", 404, 40401)
    if current_user.role == "lab_admin" and current_user.campus_id != lab.campus_id:
        raise AppError("只能管理本校区实验室设备", 403, 40314)
    with campus_db_session(campus_id) as session:
        item = Equipment(
            lab_id=lab.id,
            equipment_name=payload["equipment_name"],
            quantity=int(payload["quantity"]),
            status=payload.get("status", "active"),
            description=payload.get("description", ""),
        )
        session.add(item)
        session.commit()
        result = item.to_dict()
    return success(result, "创建设备成功")


@equipment_bp.put("/equipment/<int:equipment_id>")
@role_required("lab_admin", "system_admin")
def update_equipment(equipment_id):
    current_user = get_current_user()
    payload = request.get_json(silent=True) or {}
    item, campus_id = find_across_campuses(Equipment, equipment_id)
    if not item:
        raise AppError("equipment not found", 404, 40402)
    with campus_db_session(campus_id) as session:
        eq = session.get(Equipment, equipment_id)
        if current_user.role == "lab_admin" and current_user.campus_id != eq.lab.campus_id:
            raise AppError("只能管理本校区实验室设备", 403, 40315)
        for field in ["equipment_name", "status", "description"]:
            if field in payload:
                setattr(eq, field, payload[field])
        if "quantity" in payload:
            eq.quantity = int(payload["quantity"])
        session.commit()
        result = eq.to_dict()
    return success(result, "更新设备成功")


@equipment_bp.delete("/equipment/<int:equipment_id>")
@role_required("lab_admin", "system_admin")
def delete_equipment(equipment_id):
    current_user = get_current_user()
    item, campus_id = find_across_campuses(Equipment, equipment_id)
    if not item:
        raise AppError("equipment not found", 404, 40402)
    with campus_db_session(campus_id) as session:
        eq = session.get(Equipment, equipment_id)
        if current_user.role == "lab_admin" and current_user.campus_id != eq.lab.campus_id:
            raise AppError("只能管理本校区实验室设备", 403, 40316)
        session.delete(eq)
        session.commit()
    return success(message="删除设备成功")

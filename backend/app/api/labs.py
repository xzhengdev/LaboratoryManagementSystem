from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from app.extensions import db
from app.models import Laboratory
from app.services.reservation_service import get_lab_schedule
from app.utils.decorators import get_current_user, role_required
from app.utils.exceptions import AppError
from app.utils.response import success
from app.utils.validators import parse_date, parse_time, require_fields


lab_bp = Blueprint("labs", __name__)


@lab_bp.get("/labs")
@jwt_required()
def list_labs():
    # 实验室列表接口，支持按校区和状态筛选。
    query = Laboratory.query.order_by(Laboratory.id.asc())
    if request.args.get("campus_id"):
        query = query.filter_by(campus_id=int(request.args["campus_id"]))
    if request.args.get("status"):
        query = query.filter_by(status=request.args["status"])
    return success([item.to_dict() for item in query.all()])


@lab_bp.get("/labs/<int:lab_id>")
@jwt_required()
def lab_detail(lab_id):
    # 实验室详情接口，附带设备清单。
    item = Laboratory.query.get_or_404(lab_id)
    return success(item.to_dict({"equipment": [eq.to_dict() for eq in item.equipment]}))


@lab_bp.get("/labs/<int:lab_id>/schedule")
@jwt_required()
def lab_schedule(lab_id):
    # 查询实验室某一天排期，是预约页和 Agent 的核心接口之一。
    item = Laboratory.query.get_or_404(lab_id)
    date_str = request.args.get("date")
    if not date_str:
        raise AppError("请传入 date 参数")
    return success(get_lab_schedule(item, parse_date(date_str, "date")))


@lab_bp.post("/labs")
@role_required("lab_admin", "system_admin")
def create_lab():
    # 实验室新增：
    # 系统管理员可操作全部校区；
    # 实验室管理员只能操作自己所属校区。
    current_user = get_current_user()
    payload = request.get_json(silent=True) or {}
    require_fields(
        payload,
        ["campus_id", "lab_name", "location", "capacity", "open_time", "close_time"],
    )
    campus_id = int(payload["campus_id"])
    if current_user.role == "lab_admin" and current_user.campus_id != campus_id:
        raise AppError("只能管理本校区实验室", 403, 40310)
    item = Laboratory(
        campus_id=campus_id,
        lab_name=payload["lab_name"],
        location=payload["location"],
        capacity=int(payload["capacity"]),
        open_time=parse_time(payload["open_time"], "open_time"),
        close_time=parse_time(payload["close_time"], "close_time"),
        status=payload.get("status", "active"),
        description=payload.get("description", ""),
    )
    db.session.add(item)
    db.session.commit()
    return success(item.to_dict(), "创建实验室成功")


@lab_bp.put("/labs/<int:lab_id>")
@role_required("lab_admin", "system_admin")
def update_lab(lab_id):
    # 实验室更新接口，权限规则同新增。
    current_user = get_current_user()
    payload = request.get_json(silent=True) or {}
    item = Laboratory.query.get_or_404(lab_id)
    if current_user.role == "lab_admin" and current_user.campus_id != item.campus_id:
        raise AppError("只能更新本校区实验室", 403, 40311)

    for field in ["lab_name", "location", "status", "description"]:
        if field in payload:
            setattr(item, field, payload[field])
    if "campus_id" in payload:
        campus_id = int(payload["campus_id"])
        if current_user.role == "lab_admin" and current_user.campus_id != campus_id:
            raise AppError("不能把实验室转移到其他校区", 403, 40312)
        item.campus_id = campus_id
    if "capacity" in payload:
        item.capacity = int(payload["capacity"])
    if "open_time" in payload:
        item.open_time = parse_time(payload["open_time"], "open_time")
    if "close_time" in payload:
        item.close_time = parse_time(payload["close_time"], "close_time")
    db.session.commit()
    return success(item.to_dict(), "更新实验室成功")


@lab_bp.delete("/labs/<int:lab_id>")
@role_required("lab_admin", "system_admin")
def delete_lab(lab_id):
    # 实验室删除接口，权限规则同新增。
    current_user = get_current_user()
    item = Laboratory.query.get_or_404(lab_id)
    if current_user.role == "lab_admin" and current_user.campus_id != item.campus_id:
        raise AppError("只能删除本校区实验室", 403, 40313)
    db.session.delete(item)
    db.session.commit()
    return success(message="删除实验室成功")

from datetime import datetime

from flask import Blueprint, request

from app.extensions import db
from app.models import Campus, User
from app.utils.decorators import role_required
from app.utils.exceptions import AppError
from app.utils.response import success
from app.utils.validators import require_fields


user_bp = Blueprint("users", __name__)


def _normalize_campus_id(value):
    if value in (None, "", 0, "0"):
        return None
    return int(value)


def _ensure_username_unique(username, current_id=None):
    query = User.query.filter_by(username=username)
    if current_id:
        query = query.filter(User.id != current_id)
    if query.first():
        raise AppError("用户名已存在", 400, 40021)


def _ensure_campus_valid_for_role(role, campus_id):
    if role == "system_admin":
        return None
    if role not in ("student", "teacher", "lab_admin"):
        raise AppError("角色不合法", 400, 40022)
    if campus_id is None:
        raise AppError("该角色必须绑定校区", 400, 40023)
    campus = Campus.query.get(campus_id)
    if not campus:
        raise AppError("校区不存在", 404, 40421)
    return campus.id


def _build_role_text(role):
    return {
        "student": "学生",
        "teacher": "老师",
        "lab_admin": "实验室管理员",
        "system_admin": "系统管理员",
    }.get(role, "未知角色")


def _normalize_avatar_url(value):
    if value in (None, ""):
        return None
    avatar_url = str(value).strip()
    if not avatar_url:
        return None
    if len(avatar_url) > 500:
        raise AppError("头像地址长度不能超过 500", 400, 40025)
    return avatar_url


@user_bp.get("/users")
@role_required("system_admin")
def list_users():
    query = User.query.order_by(User.id.asc())
    if request.args.get("role"):
        query = query.filter_by(role=request.args["role"])
    if request.args.get("status"):
        query = query.filter_by(status=request.args["status"])
    if request.args.get("campus_id"):
        query = query.filter_by(campus_id=int(request.args["campus_id"]))

    keyword = (request.args.get("keyword") or "").strip().lower()
    items = query.all()
    if keyword:
        items = [
            item
            for item in items
            if keyword
            in f"{item.username}{item.real_name}{item.role}{item.campus.campus_name if item.campus else ''}".lower()
        ]
    return success(
        [item.to_dict({"role_name": _build_role_text(item.role)}) for item in items]
    )


@user_bp.post("/users")
@role_required("system_admin")
def create_user():
    payload = request.get_json(silent=True) or {}
    require_fields(payload, ["username", "real_name", "role"])

    username = str(payload["username"]).strip()
    if len(username) < 3:
        raise AppError("用户名至少 3 位", 400, 40024)
    _ensure_username_unique(username)

    role = str(payload["role"]).strip()
    campus_id = _normalize_campus_id(payload.get("campus_id"))
    campus_id = _ensure_campus_valid_for_role(role, campus_id)

    item = User(
        username=username,
        real_name=str(payload["real_name"]).strip(),
        role=role,
        campus_id=campus_id,
        phone=payload.get("phone"),
        email=payload.get("email"),
        avatar_url=_normalize_avatar_url(payload.get("avatar_url")),
        status=payload.get("status", "active"),
    )
    item.set_password(str(payload.get("password") or "123456"))
    db.session.add(item)
    db.session.commit()
    return success(
        item.to_dict({"role_name": _build_role_text(item.role)}),
        "创建用户成功",
    )


@user_bp.put("/users/<int:user_id>")
@role_required("system_admin")
def update_user(user_id):
    payload = request.get_json(silent=True) or {}
    item = User.query.get_or_404(user_id)

    if "username" in payload:
        username = str(payload["username"]).strip()
        if len(username) < 3:
            raise AppError("用户名至少 3 位", 400, 40024)
        _ensure_username_unique(username, current_id=item.id)
        item.username = username
    if "real_name" in payload:
        item.real_name = str(payload["real_name"]).strip()
    if "status" in payload:
        item.status = payload["status"]
    if "phone" in payload:
        item.phone = payload["phone"]
    if "email" in payload:
        item.email = payload["email"]
    if "avatar_url" in payload:
        item.avatar_url = _normalize_avatar_url(payload.get("avatar_url"))

    next_role = payload["role"] if "role" in payload else item.role
    next_campus_id = (
        _normalize_campus_id(payload["campus_id"])
        if "campus_id" in payload
        else item.campus_id
    )
    item.role = next_role
    item.campus_id = _ensure_campus_valid_for_role(next_role, next_campus_id)

    db.session.commit()
    return success(
        item.to_dict({"role_name": _build_role_text(item.role)}),
        "更新用户成功",
    )


@user_bp.post("/users/<int:user_id>/reset-password")
@role_required("system_admin")
def reset_password(user_id):
    payload = request.get_json(silent=True) or {}
    item = User.query.get_or_404(user_id)
    new_password = str(payload.get("password") or "123456")
    item.set_password(new_password)
    db.session.commit()
    return success(
        {"user_id": item.id, "reset_at": datetime.utcnow().isoformat()},
        "重置密码成功",
    )

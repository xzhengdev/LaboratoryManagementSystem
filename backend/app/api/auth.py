from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from app.services.auth_service import login
from app.utils.decorators import get_current_user
from app.utils.response import success
from app.utils.validators import require_fields


auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/auth/login")
def login_api():
    # 登录接口：只负责接收参数和返回 service 结果。
    payload = request.get_json(silent=True) or {}
    require_fields(payload, ["username", "password"])
    return success(
        login(payload["username"], payload["password"], payload.get("role")),
        "登录成功",
    )


@auth_bp.get("/auth/profile")
@jwt_required()
def profile_api():
    # 当前登录用户信息接口。
    return success(get_current_user().to_dict())

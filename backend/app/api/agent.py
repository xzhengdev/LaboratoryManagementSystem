from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from app.services.admin_nl_query_service import query_admin_data
from app.services.agent_service import chat
from app.utils.decorators import get_current_user, role_required
from app.utils.response import success
from app.utils.validators import require_fields


agent_bp = Blueprint("agent", __name__)


@agent_bp.post("/agent/chat")
@jwt_required()
def chat_api():
    payload = request.get_json(silent=True) or {}
    require_fields(payload, ["message"])
    current_user = get_current_user()
    result = chat(current_user, payload["message"])
    return success(result)


@agent_bp.post("/agent/admin-query")
@role_required("lab_admin", "system_admin")
def admin_query_api():
    payload = request.get_json(silent=True) or {}
    require_fields(payload, ["domain", "message"])
    current_user = get_current_user()
    context = payload.get("context") if isinstance(payload.get("context"), dict) else {}
    result = query_admin_data(
        current_user=current_user,
        domain=str(payload.get("domain") or ""),
        message=str(payload.get("message") or ""),
        context=context,
    )
    return success(result)

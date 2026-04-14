from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from app.services.agent_service import chat
from app.utils.decorators import get_current_user
from app.utils.response import success
from app.utils.validators import require_fields


agent_bp = Blueprint("agent", __name__)


@agent_bp.post("/agent/chat")
@jwt_required()
def chat_api():
    # Agent 对话接口：接收 message 文本并返回助手回复。
    payload = request.get_json(silent=True) or {}
    require_fields(payload, ["message"])
    return success(chat(get_current_user(), payload["message"]))

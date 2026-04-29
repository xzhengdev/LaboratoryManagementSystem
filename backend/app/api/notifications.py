from flask import Blueprint, request
from flask_jwt_extended import jwt_required

from app.services.notification_service import (
    get_unread_count,
    list_notifications,
    mark_all_notifications_read,
    mark_notification_read,
)
from app.utils.decorators import get_current_user
from app.utils.response import success


notification_bp = Blueprint("notifications", __name__)


@notification_bp.get("/notifications")
@jwt_required()
def list_notifications_api():
    current_user = get_current_user()
    result = list_notifications(current_user, request.args)
    return success(result)


@notification_bp.get("/notifications/unread-count")
@jwt_required()
def unread_count_api():
    current_user = get_current_user()
    return success(get_unread_count(current_user))


@notification_bp.post("/notifications/<int:notification_id>/read")
@jwt_required()
def mark_notification_read_api(notification_id):
    current_user = get_current_user()
    result = mark_notification_read(current_user, notification_id)
    return success(result, "通知已标记为已读")


@notification_bp.post("/notifications/read-all")
@jwt_required()
def mark_all_notifications_read_api():
    current_user = get_current_user()
    result = mark_all_notifications_read(current_user)
    return success(result, "通知已全部标记为已读")

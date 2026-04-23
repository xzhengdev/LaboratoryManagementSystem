from flask import Blueprint, request

from app.services.operation_log_service import list_operation_logs
from app.utils.decorators import get_current_user, role_required
from app.utils.response import success


operation_log_bp = Blueprint("operation_logs", __name__)


@operation_log_bp.get("/operation-logs")
@role_required("lab_admin", "system_admin")
def list_operation_logs_api():
    result = list_operation_logs(get_current_user(), request.args)
    return success(result)

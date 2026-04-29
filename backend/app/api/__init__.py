from .agent import agent_bp
from .approvals import approval_bp
from .assets import asset_bp
from .auth import auth_bp
from .campuses import campus_bp
from .equipment import equipment_bp
from .health import health_bp
from .lab_reports import lab_report_bp
from .labs import lab_bp
from .notifications import notification_bp
from .operation_logs import operation_log_bp
from .reservations import reservation_bp
from .statistics import statistics_bp
from .users import user_bp


def register_blueprints(app):
    # 集中注册所有业务蓝图，统一挂到 /api 前缀下。
    for blueprint in [
        auth_bp,
        campus_bp,
        lab_bp,
        equipment_bp,
        health_bp,
        reservation_bp,
        approval_bp,
        asset_bp,
        operation_log_bp,
        notification_bp,
        statistics_bp,
        user_bp,
        agent_bp,
        lab_report_bp,
    ]:
        app.register_blueprint(blueprint, url_prefix="/api")

from .agent import agent_bp
from .approvals import approval_bp
from .auth import auth_bp
from .campuses import campus_bp
from .equipment import equipment_bp
from .labs import lab_bp
from .reservations import reservation_bp
from .statistics import statistics_bp


def register_blueprints(app):
    # 集中注册所有业务蓝图，统一挂到 /api 前缀下。
    for blueprint in [
        auth_bp,
        campus_bp,
        lab_bp,
        equipment_bp,
        reservation_bp,
        approval_bp,
        statistics_bp,
        agent_bp,
    ]:
        app.register_blueprint(blueprint, url_prefix="/api")

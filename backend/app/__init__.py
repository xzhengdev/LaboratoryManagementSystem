import os

from flask import Flask

from app.api import register_blueprints
from app.config import DevelopmentConfig
from app.extensions import cors, db, jwt, migrate
from app.utils.exceptions import AppError
from app.utils.response import fail


def register_error_handlers(app):
    # 统一注册异常处理：
    # 业务异常走 AppError，404 / 500 也统一包装成 JSON。
    @app.errorhandler(AppError)
    def handle_app_error(error):
        return fail(error.message, error.code, error.error_code)

    @app.errorhandler(404)
    def handle_404(_error):
        return fail("资源不存在", 404, 40400)

    @app.errorhandler(500)
    def handle_500(error):
        app.logger.exception(error)
        return fail("服务器内部错误", 500, 50000)


def register_cli(app):
    # 提供 flask seed-data 命令，便于一键初始化演示数据。
    @app.cli.command("seed-data")
    def seed_data_command():
        from scripts.seed import seed_data

        seed_data()
        print("seed 数据初始化完成")


def create_app(config_class=DevelopmentConfig):
    # 手动指定 instance 目录到 backend/instance，
    # 避免在某些 Windows 环境下默认实例路径没有权限。
    backend_root = os.path.dirname(os.path.dirname(__file__))
    instance_path = os.path.join(backend_root, "instance")
    os.makedirs(instance_path, exist_ok=True)

    # 创建 Flask 应用并载入配置。
    app = Flask(__name__, instance_path=instance_path)
    app.config.from_object(config_class)

    # 初始化扩展。
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": "*"}})

    # 注册蓝图、异常处理和 CLI 命令。
    register_blueprints(app)
    register_error_handlers(app)
    register_cli(app)
    return app

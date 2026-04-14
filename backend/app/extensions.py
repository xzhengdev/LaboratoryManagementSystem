from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy


# 统一在这里声明 Flask 扩展对象，避免循环导入。
# 真正的 init_app 会在 app/__init__.py 中完成。
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
cors = CORS()

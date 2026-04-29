from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

try:
    import redis
except Exception:  # pragma: no cover - import fallback
    redis = None


# 统一在这里声明 Flask 扩展对象，避免循环导入。
# 真正的 init_app 会在 app/__init__.py 中完成。
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
cors = CORS()
redis_client = None


def init_redis(app):
    # 按配置初始化 Redis 客户端。若未配置或连接失败，降级为 None。
    global redis_client

    redis_url = (app.config.get("REDIS_URL") or "").strip()
    if not redis_url:
        redis_client = None
        return

    if redis is None:
        app.logger.warning("redis 依赖未安装，已禁用分布式锁相关能力")
        redis_client = None
        return

    try:
        client = redis.Redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=1,
            # 允许 BLPOP 等阻塞命令正常等待，避免异步 worker 误超时退出。
            socket_timeout=10,
        )
        client.ping()
        redis_client = client
        app.logger.info("Redis 客户端初始化成功")
    except Exception as exc:  # pragma: no cover - 运行环境相关
        app.logger.warning("Redis 连接失败，已降级为本地模式: %s", exc)
        redis_client = None

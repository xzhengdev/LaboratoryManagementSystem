import os

from dotenv import load_dotenv


load_dotenv()


def build_database_uri():
    # 优先使用完整 DATABASE_URL，方便未来切换到生产环境或云数据库。
    direct_uri = os.getenv("DATABASE_URL")
    if direct_uri:
        return direct_uri

    # 如果没有完整连接串，则尝试按 MySQL 分字段拼接。
    mysql_host = os.getenv("MYSQL_HOST")
    mysql_user = os.getenv("MYSQL_USER")
    mysql_password = os.getenv("MYSQL_PASSWORD")
    mysql_db = os.getenv("MYSQL_DB")
    mysql_port = os.getenv("MYSQL_PORT", "3306")

    if all([mysql_host, mysql_user, mysql_password, mysql_db]):
        return (
            f"mysql+pymysql://{mysql_user}:{mysql_password}"
            f"@{mysql_host}:{mysql_port}/{mysql_db}?charset=utf8mb4"
        )

    # 都没有配置时回退到 sqlite，方便本地演示和答辩。
    return "sqlite:///lab_dev.db"


class Config:
    # Flask 基础安全配置。
    SECRET_KEY = os.getenv(
        "SECRET_KEY", "lab-reservation-secret-key-for-dev-2026"
    )
    JWT_SECRET_KEY = os.getenv(
        "JWT_SECRET_KEY", "lab-jwt-secret-key-for-dev-2026-32bytes"
    )
    SQLALCHEMY_DATABASE_URI = build_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # 关闭 JSON ASCII 转义，保证中文直接输出而不是 \uXXXX。
    JSON_AS_ASCII = False

    # Agent 相关配置：
    # rule 表示走本地规则助手，openai 表示调用兼容 OpenAI 的对话接口。
    AGENT_PROVIDER = os.getenv("AGENT_PROVIDER", "rule")
    AGENT_MODEL = os.getenv("AGENT_MODEL", "gpt-4o-mini")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL = os.getenv(
        "OPENAI_BASE_URL", "https://api.openai.com/v1/chat/completions"
    )


class DevelopmentConfig(Config):
    # 本项目默认使用开发配置，便于调试和本地联调。
    DEBUG = True

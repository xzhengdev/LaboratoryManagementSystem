import os

from dotenv import load_dotenv


load_dotenv()


def build_database_uri():
    direct_uri = os.getenv("DATABASE_URL")
    if direct_uri:
        return direct_uri

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

    return "sqlite:///lab_dev.db"


def default_agent_model(provider):
    if provider == "deepseek":
        return "deepseek-chat"
    return "gpt-4o-mini"


def build_llm_base_url(provider):
    if provider == "deepseek":
        return "https://api.deepseek.com/chat/completions"
    return "https://api.openai.com/v1/chat/completions"


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "lab-reservation-secret-key-for-dev-2026")
    JWT_SECRET_KEY = os.getenv(
        "JWT_SECRET_KEY", "lab-jwt-secret-key-for-dev-2026-32bytes"
    )
    SQLALCHEMY_DATABASE_URI = build_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024
    JSON_AS_ASCII = False
    UPLOAD_DIRNAME = os.getenv("UPLOAD_DIRNAME", "uploads")

    AGENT_PROVIDER = os.getenv("AGENT_PROVIDER", "rule").strip().lower()
    AGENT_MODEL = os.getenv(
        "AGENT_MODEL",
        os.getenv("LLM_MODEL", default_agent_model(AGENT_PROVIDER)),
    )
    LLM_API_KEY = (
        os.getenv("LLM_API_KEY")
        or os.getenv("DEEPSEEK_API_KEY")
        or os.getenv("OPENAI_API_KEY", "")
    )
    LLM_BASE_URL = os.getenv(
        "LLM_BASE_URL",
        os.getenv(
            "DEEPSEEK_BASE_URL",
            os.getenv("OPENAI_BASE_URL", build_llm_base_url(AGENT_PROVIDER)),
        ),
    )
    # Keep old names for backward compatibility.
    OPENAI_API_KEY = LLM_API_KEY
    OPENAI_BASE_URL = LLM_BASE_URL


class DevelopmentConfig(Config):
    DEBUG = True

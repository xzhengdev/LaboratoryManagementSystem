"""
配置模块 - 负责加载环境变量并构建应用配置
功能：从 .env 文件读取配置，提供数据库连接、LLM模型配置等
"""
import os  # 用于读取环境变量
from dotenv import load_dotenv  # 从 .env 文件加载环境变量到系统环境
# ==================== 加载 .env 文件 ====================
# 读取项目根目录下的 .env 文件，将里面的键值对设置为环境变量
load_dotenv()
# ==================== 数据库连接字符串构建 ====================
def build_database_uri():
    """
    构建数据库连接URI（统一资源标识符）
    优先级：DATABASE_URL 环境变量 > MySQL配置 > SQLite默认配置
    
    返回示例：
        - mysql+pymysql://user:pass@host:3306/db?charset=utf8mb4
        - sqlite:///lab_dev.db
    """
    # 方式1：直接读取完整的数据连接字符串
    direct_uri = os.getenv("DATABASE_URL")
    if direct_uri:
        return direct_uri  # 如果配置了完整URI，直接返回

    # 方式2：从环境变量分别读取MySQL的各部分配置
    mysql_host = os.getenv("MYSQL_HOST")          # MySQL服务器地址
    mysql_user = os.getenv("MYSQL_USER")          # 数据库用户名
    mysql_password = os.getenv("MYSQL_PASSWORD")  # 数据库密码
    mysql_db = os.getenv("MYSQL_DB")              # 数据库名称
    mysql_port = os.getenv("MYSQL_PORT", "3306")  # MySQL端口，默认3306

    # 检查MySQL必需配置是否完整（all() 确保所有值都存在）
    if all([mysql_host, mysql_user, mysql_password, mysql_db]):
        # 使用 PyMySQL 驱动连接 MySQL，指定 utf8mb4 字符集支持emoji
        return (
            f"mysql+pymysql://{mysql_user}:{mysql_password}"
            f"@{mysql_host}:{mysql_port}/{mysql_db}?charset=utf8mb4"
        )


# ==================== LLM模型默认值获取 ====================
def default_agent_model(provider):
    """
    根据 AI 服务提供商返回默认的模型名称
    参数：
        provider - AI服务提供商名称（如 "deepseek", "openai"）
    
    返回：
        deepseek-chat  - DeepSeek 的默认模型
        gpt-4o-mini    - OpenAI 的默认模型（性价比高的轻量模型）
    """
    if provider == "deepseek":
        return "deepseek-chat"      # DeepSeek 对话模型
    return "gpt-4o-mini"            # OpenAI 的 GPT-4 mini 模型


def build_llm_base_url(provider):
    """
    根据 AI 服务提供商返回对应的 API 端点地址
    参数：
        provider - AI服务提供商名称
    返回：
        DeepSeek API 地址 或 OpenAI API 地址
    """
    if provider == "deepseek":
        return "https://api.deepseek.com/chat/completions"  # DeepSeek API
    return "https://api.openai.com/v1/chat/completions"     # OpenAI API


# ==================== 基础配置类 ====================
class Config:
    """
    应用基础配置类
    包含所有环境通用的配置项，可被子类继承覆盖
    """
    # ---------- 安全相关配置 ----------
    # Flask 会话加密密钥（用于加密 session）
    SECRET_KEY = os.getenv("SECRET_KEY", "lab-reservation-secret-key-for-dev-2026")
    # JWT（JSON Web Token）签名密钥（用于用户认证令牌）
    JWT_SECRET_KEY = os.getenv(
        "JWT_SECRET_KEY", "lab-jwt-secret-key-for-dev-2026-32bytes"
    )

    # ---------- 数据库配置 ----------
    # SQLAlchemy 数据库连接字符串（通过上面的函数动态构建）
    SQLALCHEMY_DATABASE_URI = build_database_uri()
    # 关闭 SQLAlchemy 的对象修改追踪（提升性能，减少内存开销）
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ---------- 文件上传配置 ----------
    # 最大请求内容大小限制：10MB（防止恶意大文件攻击）
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024  # 10MB = 10 * 1024KB * 1024B

    # ---------- JSON 响应配置 ----------
    # 允许 JSON 响应中包含中文（不转义为 Unicode 编码）
    JSON_AS_ASCII = False

    # ---------- 文件存储配置 ----------
    # 上传文件的存放目录名（默认为 uploads）
    UPLOAD_DIRNAME = os.getenv("UPLOAD_DIRNAME", "uploads")

    # ---------- AI 助手（Agent）配置 ----------
    # AI 服务提供商：支持 "rule"（规则引擎）、"deepseek"、"openai" 等
    # strip() 去除首尾空格，lower() 转为小写统一格式
    AGENT_PROVIDER = os.getenv("AGENT_PROVIDER", "rule").strip().lower()
    
    # AI 使用的具体模型名称
    # 优先级：环境变量 AGENT_MODEL > LLM_MODEL > 根据 provider 生成的默认模型
    AGENT_MODEL = os.getenv(
        "AGENT_MODEL",
        os.getenv("LLM_MODEL", default_agent_model(AGENT_PROVIDER)),
    )
    
    # LLM API 密钥（用于调用大语言模型接口）
    # 优先级：LLM_API_KEY > DEEPSEEK_API_KEY > OPENAI_API_KEY > 空字符串
    LLM_API_KEY = (
        os.getenv("LLM_API_KEY")
        or os.getenv("DEEPSEEK_API_KEY")
        or os.getenv("OPENAI_API_KEY", "")
    )
    
    # LLM API 基础地址
    # 优先级：LLM_BASE_URL > DEEPSEEK_BASE_URL > OPENAI_BASE_URL > 根据 provider 生成的默认地址
    LLM_BASE_URL = os.getenv(
        "LLM_BASE_URL",
        os.getenv(
            "DEEPSEEK_BASE_URL",
            os.getenv("OPENAI_BASE_URL", build_llm_base_url(AGENT_PROVIDER)),
        ),
    )
    
    # 为了向后兼容，保留旧的配置变量名（供旧代码使用）
    OPENAI_API_KEY = LLM_API_KEY      # 旧版代码可能使用 OPENAI_API_KEY
    OPENAI_BASE_URL = LLM_BASE_URL    # 旧版代码可能使用 OPENAI_BASE_URL


# ==================== 开发环境配置 ====================
class DevelopmentConfig(Config):
    """
    开发环境专用配置类
    继承 Config，并开启调试模式
    """
    # 开启调试模式：代码修改自动重载、显示详细错误信息
    DEBUG = True
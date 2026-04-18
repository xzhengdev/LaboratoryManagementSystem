"""
AI助手蓝图 (agent_bp)
功能：提供智能对话服务，帮助用户查询实验室、预约等信息
支持：规则匹配 + LLM（大语言模型）两种模式
"""
from flask import Blueprint, request              # Flask核心：蓝图、请求对象
from flask_jwt_extended import jwt_required      # JWT装饰器：要求请求携带有效令牌
from app.services.agent_service import chat       # AI对话服务
from app.utils.decorators import get_current_user # 获取当前登录用户
from app.utils.response import success            # 统一成功响应格式
from app.utils.validators import require_fields   # 验证必填字段
# ==================== 蓝图创建 ====================
agent_bp = Blueprint("agent", __name__)
# ==================== AI对话接口 ====================
@agent_bp.post("/agent/chat")
@jwt_required()  # 需要JWT认证（所有登录用户均可使用）
def chat_api():
    """
    AI助手对话接口
    功能：
        - 接收用户问题，返回智能回复
        - 支持查询实验室、预约、设备等信息
        - 可根据配置使用规则引擎或 LLM
    支持的问题类型：
        - 实验室查询："有哪些实验室？"、"计算机实验室在哪里？"
        - 预约相关："帮我预约实验室"、"我的预约状态"
        - 设备查询："实验室有哪些设备？"
        - 使用帮助："怎么预约实验室？"
    """
    # 获取请求JSON，解析失败时返回空字典
    payload = request.get_json(silent=True) or {}
    # 验证必填字段：message（用户消息）
    require_fields(payload, ["message"])
    # 获取当前登录用户（用于个性化回复，如查看自己的预约）
    current_user = get_current_user()
    # 调用 AI 服务处理消息
    # chat 函数会根据配置选择：
    #   - AGENT_PROVIDER="rule"     : 使用规则匹配（关键词+正则）
    #   - AGENT_PROVIDER="deepseek" : 使用 DeepSeek API
    #   - AGENT_PROVIDER="openai"   : 使用 OpenAI API
    result = chat(current_user, payload["message"])
    
    # 返回 AI 回复结果
    return success(result)
"""
异步事件发布模块
用于将业务事件推送到 Redis 队列，供后台消费者处理
"""

import json
from datetime import datetime, timezone

from flask import current_app

import app.extensions as app_extensions


def _event_enabled():
    """检查是否开启异步事件功能"""
    return bool(current_app.config.get("ENABLE_ASYNC_EVENTS", False))


def publish_async_event(event_type, payload):
    """
    发布异步事件到 Redis 队列
    
    参数:
        event_type: 事件类型，如 "budget_changed", "request_approved"
        payload: 事件携带的数据字典
    
    返回:
        True 表示事件已入队，False 表示功能未启用或发布失败
    """
    if not _event_enabled():
        return False

    redis_client = app_extensions.redis_client
    if redis_client is None:
        current_app.logger.warning("Async events enabled but Redis client is unavailable")
        return False

    queue_name = str(current_app.config.get("ASYNC_EVENT_QUEUE_NAME", "lab:events"))
    event = {
        "type": str(event_type or "").strip(),
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "payload": payload or {},
    }
    try:
        redis_client.rpush(queue_name, json.dumps(event, ensure_ascii=False))
        return True
    except Exception as exc:
        current_app.logger.warning("Failed to publish async event: %s", exc)
        return False
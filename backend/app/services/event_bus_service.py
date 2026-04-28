import json
from datetime import datetime, timezone

from flask import current_app

import app.extensions as app_extensions


def _event_enabled():
    return bool(current_app.config.get("ENABLE_ASYNC_EVENTS", False))


def publish_async_event(event_type, payload):
    """
    Publish lightweight async events to Redis list.
    Returns True when the event is queued, False when disabled/unavailable.
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
    except Exception as exc:  # pragma: no cover - runtime env dependent
        current_app.logger.warning("Failed to publish async event: %s", exc)
        return False

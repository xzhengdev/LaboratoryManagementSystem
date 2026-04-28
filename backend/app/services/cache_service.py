import json
from datetime import date

from flask import current_app

import app.extensions as app_extensions

LAB_SCHEDULE_CACHE_PREFIX = "cache:lab_schedule:"
STATISTICS_CACHE_PREFIX = "cache:statistics:"


def _redis_client():
    return app_extensions.redis_client


def _safe_json_loads(raw):
    try:
        value = json.loads(raw)
        return value
    except Exception:
        return None


def _safe_json_dumps(value):
    try:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        return None


def _get_ttl(config_key, default_value):
    try:
        return max(1, int(current_app.config.get(config_key, default_value)))
    except Exception:
        return default_value


def lab_schedule_cache_key(lab_id, reservation_date):
    if isinstance(reservation_date, date):
        date_text = reservation_date.isoformat()
    else:
        date_text = str(reservation_date)
    return f"{LAB_SCHEDULE_CACHE_PREFIX}{lab_id}:{date_text}"


def get_cached_lab_schedule(lab_id, reservation_date):
    client = _redis_client()
    if client is None:
        return None
    key = lab_schedule_cache_key(lab_id, reservation_date)
    try:
        raw = client.get(key)
        if not raw:
            return None
        return _safe_json_loads(raw)
    except Exception:
        return None


def set_cached_lab_schedule(lab_id, reservation_date, payload):
    client = _redis_client()
    if client is None:
        return
    key = lab_schedule_cache_key(lab_id, reservation_date)
    serialized = _safe_json_dumps(payload)
    if not serialized:
        return
    ttl = _get_ttl("LAB_SCHEDULE_CACHE_TTL_SECONDS", 30)
    try:
        client.setex(key, ttl, serialized)
    except Exception:
        return


def invalidate_lab_schedule_cache(lab_id, reservation_date=None):
    client = _redis_client()
    if client is None:
        return
    if reservation_date is not None:
        key = lab_schedule_cache_key(lab_id, reservation_date)
        try:
            client.delete(key)
        except Exception:
            return
        return

    pattern = f"{LAB_SCHEDULE_CACHE_PREFIX}{lab_id}:*"
    try:
        for key in client.scan_iter(match=pattern, count=200):
            client.delete(key)
    except Exception:
        return


def statistics_cache_key(name, campus_id=None):
    campus_key = "all" if campus_id is None else str(campus_id)
    return f"{STATISTICS_CACHE_PREFIX}{name}:{campus_key}"


def get_cached_statistics(name, campus_id=None):
    client = _redis_client()
    if client is None:
        return None
    key = statistics_cache_key(name, campus_id)
    try:
        raw = client.get(key)
        if not raw:
            return None
        return _safe_json_loads(raw)
    except Exception:
        return None


def set_cached_statistics(name, campus_id, payload):
    client = _redis_client()
    if client is None:
        return
    key = statistics_cache_key(name, campus_id)
    serialized = _safe_json_dumps(payload)
    if not serialized:
        return
    ttl = _get_ttl("STATISTICS_CACHE_TTL_SECONDS", 45)
    try:
        client.setex(key, ttl, serialized)
    except Exception:
        return


def invalidate_statistics_cache():
    client = _redis_client()
    if client is None:
        return
    pattern = f"{STATISTICS_CACHE_PREFIX}*"
    try:
        for key in client.scan_iter(match=pattern, count=200):
            client.delete(key)
    except Exception:
        return


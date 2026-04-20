from datetime import datetime
from typing import Any, Callable, Dict

# 定义一个空的预约表单结构，后续用户逐步提供信息时填充这个字典。
def _default_reservation_form() -> Dict[str, Any]:
    return {
        "date": "",
        "start_time": "",
        "end_time": "",
        "participant_count": None,
        "purpose": "",
        "lab_id": None,
        "campus": "",
        "type": "",
        "preference": "",
    }

# 从存储中获取用户会话，如果过期则重置。
def clean_session(
    store: Dict[int, Dict[str, Any]],
    user_id: int,
    now_fn: Callable[[], datetime],
    ttl_minutes: int,
) -> Dict[str, Any]:
    now = now_fn()
    session = store.get(user_id) or {}
    last = session.get("updated_at")
    if not last or (now - last).total_seconds() > ttl_minutes * 60:
        session = {}

    session.setdefault("reservation_form", _default_reservation_form())
    session.setdefault("last_labs", [])
    session.setdefault("last_reservations", [])
    session.setdefault("last_recommended_time", {})
    session.setdefault("pending_action", None)
    session.setdefault("followup_context", None)
    session.setdefault("updated_at", now)
    session.setdefault("last_choice_type", "")

    store[user_id] = session
    return session

# 更新会话的 updated_at 并保存到存储中。
def save_session(
    store: Dict[int, Dict[str, Any]],
    user_id: int,
    session: Dict[str, Any],
    now_fn: Callable[[], datetime],
) -> None:
    session["updated_at"] = now_fn()
    store[user_id] = session

# 清空用户当前的所有预约相关状态，通常用于：
def reset_form(session: Dict[str, Any]) -> None:
    session["reservation_form"] = _default_reservation_form()
    session["last_labs"] = []
    session["last_recommended_time"] = {}
    session["last_choice_type"] = ""
    session["pending_action"] = None
    session["followup_context"] = None

# ┌─────────────────────────────────────────────────────┐
# │                   会话存储 (store)                    │
# │  {                                                  │
# │    12345: {  # user_id                              │
# │        "reservation_form": {...},                   │
# │        "last_labs": [...],                          │
# │        "pending_action": {...},                     │
# │        "updated_at": datetime(...)                  │
# │    },                                               │
# │    67890: {...}                                     │
# │  }                                                  │
# └─────────────────────────────────────────────────────┘
#                         ↑
#                         │
#         ┌───────────────┼───────────────┐
#         │               │               │
#    clean_session    save_session    reset_form
#    (获取/初始化)    (保存更新)      (重置状态)
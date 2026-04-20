from datetime import datetime
from typing import Any, Callable, Dict


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


def save_session(
    store: Dict[int, Dict[str, Any]],
    user_id: int,
    session: Dict[str, Any],
    now_fn: Callable[[], datetime],
) -> None:
    session["updated_at"] = now_fn()
    store[user_id] = session


def reset_form(session: Dict[str, Any]) -> None:
    session["reservation_form"] = _default_reservation_form()
    session["last_labs"] = []
    session["last_recommended_time"] = {}
    session["last_choice_type"] = ""
    session["pending_action"] = None
    session["followup_context"] = None

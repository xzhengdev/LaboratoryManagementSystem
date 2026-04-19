import json
import re
from datetime import date, datetime, time, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

import requests

from app.config import Config
from app.models import Laboratory, Reservation
from app.services.reservation_service import cancel_reservation, create_reservation, get_lab_schedule
from app.utils.exceptions import AppError


ACTIVE_RESERVATION_STATUSES = {"pending", "approved"}
SESSION_TTL_MINUTES = 60
MAX_AGENT_STEPS = 5
MAX_TOOL_REPEAT_STEPS = 2
MAX_HISTORY_SUMMARY_CHARS = 280

AGENT_TOOL_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "query_labs": {
        "required": [],
        "optional": ["date", "campus", "type", "participant_count"],
    },
    "query_schedule": {
        "required": ["date"],
        "optional": ["lab_id"],
    },
    "recommend_time": {
        "required": ["date"],
        "optional": ["lab_id", "preference"],
    },
    "create_reservation": {
        "required": ["lab_id", "date", "start_time", "end_time", "participant_count", "purpose"],
        "optional": [],
    },
    "my_reservations": {
        "required": [],
        "optional": [],
    },
    "cancel_reservation": {
        "required": ["reservation_id"],
        "optional": [],
    },
    "navigate": {
        "required": ["path"],
        "optional": [],
    },
}

AGENT_SESSIONS: Dict[int, Dict[str, Any]] = {}


def _now() -> datetime:
    return datetime.now()


def _today() -> date:
    return date.today()


def _new_trace_id() -> str:
    return f"agt-{uuid4().hex[:12]}"


def _tool_call(tool: str, params: Dict[str, Any], reply: str) -> Dict[str, Any]:
    return {
        "type": "tool_call",
        "tool": tool,
        "params": params,
        "reply": reply,
    }


def _tool_result(
    tool: str,
    ok: bool,
    data: str,
    *,
    error_code: str = "",
    error_message: str = "",
    raw: Optional[Any] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "ok": ok,
        "tool": tool,
        "data": data,
        "error_code": error_code,
        "error_message": error_message,
    }
    if raw is not None:
        result["raw"] = raw
    if extra:
        result.update(extra)
    return result


def _normalize_params_shape(params: Any) -> Dict[str, Any]:
    if isinstance(params, dict):
        return dict(params)
    return {}


def _safe_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except Exception:
        return None


def _sanitize_tool_params(tool: str, params: Dict[str, Any]) -> Dict[str, Any]:
    schema = AGENT_TOOL_SCHEMAS.get(tool) or {}
    keys = set(schema.get("required") or []).union(schema.get("optional") or [])
    cleaned: Dict[str, Any] = {}
    for key in keys:
        if key not in params:
            continue
        value = params.get(key)
        if key in {"participant_count", "lab_id", "reservation_id"}:
            casted = _safe_int(value)
            if casted is not None:
                cleaned[key] = casted
            continue
        if isinstance(value, str):
            cleaned[key] = value.strip()
        elif value is not None:
            cleaned[key] = str(value).strip()
    return cleaned


def _missing_required_tool_fields(tool: str, params: Dict[str, Any]) -> List[str]:
    schema = AGENT_TOOL_SCHEMAS.get(tool) or {}
    missing = []
    for key in schema.get("required") or []:
        value = params.get(key)
        if value is None or value == "":
            missing.append(key)
    return missing


def _missing_fields_hint(tool: str, missing: List[str]) -> str:
    if tool == "create_reservation":
        label_map = {
            "lab_id": "实验室ID",
            "date": "预约日期(YYYY-MM-DD)",
            "start_time": "开始时间(HH:MM)",
            "end_time": "结束时间(HH:MM)",
            "participant_count": "参与人数",
            "purpose": "用途说明",
        }
        return "还缺少这些信息: " + "、".join([label_map.get(x, x) for x in missing]) + "。"
    if tool == "query_schedule":
        return "请先告诉我日期，例如 2026-04-20。"
    if tool == "cancel_reservation":
        return "请告诉我要取消的预约ID，例如：取消预约ID 23。"
    return "参数不完整，请补充必要信息后重试。"


def _rules_context() -> str:
    text = str(getattr(Config, "AGENT_RULES_CONTEXT", "") or "")
    if text.strip():
        return text
    return (
        "实验室预约规则: 预约必须在实验室开放时间内，开始时间早于结束时间; "
        "预约开始至少晚于当前时间30分钟，预约日期不能超过未来7天; "
        "参与人数不可超过实验室容量; 同一用户不能重叠预约。"
    )


def _extract_min_advance_days(ctx: str) -> int:
    m = re.search(r"提前\s*(\d+)\s*天", ctx)
    if m:
        return int(m.group(1))
    return 0


def _forbid_duplicate(ctx: str) -> bool:
    return "重叠预约" in ctx or "重复预约" in ctx


def _safe_json_loads(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    content = text.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?", "", content, flags=re.IGNORECASE).strip()
        content = re.sub(r"```$", "", content).strip()
    try:
        data = json.loads(content)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    m = re.search(r"(\{.*\})", content, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(1))
            if isinstance(data, dict):
                return data
        except Exception:
            return None
    return None


def _call_llm_messages(messages: List[Dict[str, str]], temperature: float = 0.1) -> str:
    if not Config.LLM_API_KEY:
        raise RuntimeError("missing LLM_API_KEY")
    headers = {
        "Authorization": f"Bearer {Config.LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": Config.AGENT_MODEL,
        "messages": messages,
        "temperature": temperature,
    }
    resp = requests.post(Config.LLM_BASE_URL, headers=headers, json=payload, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    return str(data["choices"][0]["message"]["content"]).strip()


def _call_general_llm(user, message: str) -> str:
    if Config.AGENT_PROVIDER not in {"openai", "deepseek", "llm"} or not Config.LLM_API_KEY:
        return "我可以优先帮你处理实验室相关问题，比如查空闲时段、创建预约、取消预约。"
    try:
        return _call_llm_messages(
            [
                {"role": "system", "content": "你是简洁可靠的中文助手。"},
                {"role": "user", "content": message},
            ],
            temperature=0.3,
        )
    except Exception:
        return "我暂时无法连接通用模型，请稍后重试。"


def _clean_session(user_id: int) -> Dict[str, Any]:
    now = _now()
    session = AGENT_SESSIONS.get(user_id) or {}
    last = session.get("updated_at")
    if not last or (now - last).total_seconds() > SESSION_TTL_MINUTES * 60:
        session = {}
    session.setdefault(
        "reservation_form",
        {
            "date": "",
            "start_time": "",
            "end_time": "",
            "participant_count": None,
            "purpose": "",
            "lab_id": None,
            "campus": "",
            "type": "",
        },
    )
    session.setdefault("last_labs", [])
    session.setdefault("last_reservations", [])
    session.setdefault("updated_at", now)
    AGENT_SESSIONS[user_id] = session
    return session


def _save_session(user_id: int, session: Dict[str, Any]) -> None:
    session["updated_at"] = _now()
    AGENT_SESSIONS[user_id] = session


def _reset_form(session: Dict[str, Any]) -> None:
    session["reservation_form"] = {
        "date": "",
        "start_time": "",
        "end_time": "",
        "participant_count": None,
        "purpose": "",
        "lab_id": None,
        "campus": "",
        "type": "",
    }
    session["last_labs"] = []


def _detect_date(text: str) -> Optional[str]:
    msg = text or ""
    today = _today()
    if "今天" in msg:
        return today.isoformat()
    if "明天" in msg:
        return (today + timedelta(days=1)).isoformat()
    if "后天" in msg:
        return (today + timedelta(days=2)).isoformat()
    m = re.search(r"(20\d{2}-\d{1,2}-\d{1,2})", msg)
    if m:
        try:
            y, mo, d = [int(i) for i in m.group(1).split("-")]
            return date(y, mo, d).isoformat()
        except Exception:
            return None
    m2 = re.search(r"(\d{1,2})月(\d{1,2})日", msg)
    if m2:
        try:
            return date(today.year, int(m2.group(1)), int(m2.group(2))).isoformat()
        except Exception:
            return None
    return None


def _normalize_clock(hour: int, minute: int, period: Optional[str]) -> str:
    h = max(0, min(23, hour))
    m = max(0, min(59, minute))
    if period in {"下午", "晚上"} and h < 12:
        h += 12
    if period == "中午" and h < 11:
        h += 12
    if period == "上午" and h == 12:
        h = 0
    return f"{h:02d}:{m:02d}"


def _detect_time_range(text: str) -> Tuple[Optional[str], Optional[str]]:
    msg = text or ""
    m = re.search(r"(\d{1,2}:\d{2})\s*(?:-|到|至)\s*(\d{1,2}:\d{2})", msg)
    if m:
        return m.group(1), m.group(2)
    m2 = re.search(
        r"(上午|下午|晚上|中午)?\s*(\d{1,2})点(?:([0-5]?\d)分?)?\s*(?:-|到|至)\s*(上午|下午|晚上|中午)?\s*(\d{1,2})点(?:([0-5]?\d)分?)?",
        msg,
    )
    if m2:
        p1, h1, m1, p2, h2, m2_ = m2.groups()
        return _normalize_clock(int(h1), int(m1 or 0), p1), _normalize_clock(int(h2), int(m2_ or 0), p2)
    return None, None


def _detect_participant_count(text: str) -> Optional[int]:
    m = re.search(r"(\d{1,3})\s*人", text or "")
    if m:
        return int(m.group(1))
    return None


def _detect_purpose(text: str) -> Optional[str]:
    msg = (text or "").strip()
    m = re.search(r"(?:用途|用于|目的)[:：]?\s*(.+)$", msg)
    if m:
        return m.group(1).strip()[:120]
    return None


def _detect_campus(text: str) -> str:
    msg = text or ""
    for key in ["海淀", "朝阳", "通州", "新校区", "校本部", "丰台", "校区"]:
        if key in msg:
            return key
    return ""


def _detect_type(text: str) -> str:
    msg = text or ""
    for key in ["计算机", "化学", "物理", "生物", "电子", "语音", "AI", "人工智能"]:
        if key.lower() in msg.lower():
            return key
    return ""


def _detect_lab_id_or_choice(text: str, session: Dict[str, Any]) -> Optional[int]:
    msg = (text or "").strip()
    m = re.search(r"(?:实验室ID|lab_id|ID)[:：]?\s*(\d+)", msg, re.IGNORECASE)
    if m:
        return int(m.group(1))
    m2 = re.match(r"^\D*(\d{1,2})\D*$", msg)
    if m2 and session.get("last_labs"):
        idx = int(m2.group(1))
        labs = session["last_labs"]
        if 1 <= idx <= len(labs):
            return int(labs[idx - 1]["id"])
    return None


def _detect_reservation_id_or_choice(text: str, session: Dict[str, Any]) -> Optional[int]:
    msg = (text or "").strip()
    m = re.search(r"(?:reservation_id|预约ID|预约id|ID)[:：#\s]*(\d+)", msg, re.IGNORECASE)
    if m:
        return int(m.group(1))
    m2 = re.match(r"^\D*(\d{1,2})\D*$", msg)
    if m2 and session.get("last_reservations"):
        idx = int(m2.group(1))
        rows = session["last_reservations"]
        if 1 <= idx <= len(rows):
            return int(rows[idx - 1]["id"])
    return None


def _to_minutes(hhmm: str) -> int:
    h, m = [int(i) for i in hhmm.split(":")]
    return h * 60 + m


def _llm_extract_form(text: str, form: Dict[str, Any]) -> Dict[str, Any]:
    if not Config.LLM_API_KEY:
        return form
    prompt = f"抽取预约字段并仅返回JSON。已有表单: {json.dumps(form, ensure_ascii=False)}。用户输入: {text}"
    try:
        content = _call_llm_messages(
            [
                {"role": "system", "content": "你是严格 JSON 输出的抽取助手。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
        )
        parsed = _safe_json_loads(content) or {}
        for key in ["date", "start_time", "end_time", "purpose", "campus", "type"]:
            if parsed.get(key):
                form[key] = parsed[key]
        if parsed.get("participant_count") is not None:
            iv = _safe_int(parsed.get("participant_count"))
            if iv is not None:
                form["participant_count"] = iv
        if parsed.get("lab_id") is not None:
            iv = _safe_int(parsed.get("lab_id"))
            if iv is not None:
                form["lab_id"] = iv
    except Exception:
        pass
    return form


def _extract_intent(text: str) -> str:
    msg = (text or "").strip().lower()
    if any(k in msg for k in ["取消预约", "cancel reservation", "cancel_reservation"]):
        return "cancel_reservation"
    if any(k in msg for k in ["不需要预约", "不用预约", "先不预约", "不约了", "取消当前预约", "退出预约"]):
        return "cancel_flow"
    if any(k in msg for k in ["去预约页面", "去排期页面", "跳转", "打开页面", "进入页面"]):
        return "navigate"
    if any(k in msg for k in ["我的预约", "我有哪些预约", "预约列表"]):
        return "my_reservations"
    if any(k in msg for k in ["推荐时间", "什么时候有空", "什么时候空", "帮我推荐时间"]):
        return "recommend_time"
    if any(k in msg for k in ["排期", "有没有空", "是否空闲", "schedule"]):
        return "query_schedule"
    if any(k in msg for k in ["预约", "预定"]):
        return "create_reservation"
    if any(k in msg for k in ["有哪些实验室", "查询实验室", "可用实验室", "空闲实验室", "实验室", "lab"]):
        return "query_labs"
    return "general"


def _is_lab_related(text: str) -> bool:
    msg = (text or "").lower()
    keys = ["实验室", "预约", "排期", "空闲", "lab", "schedule", "reservation", "校区", "设备", "取消预约"]
    return any(k in msg for k in keys)


def _is_cancel_flow_message(text: str) -> bool:
    msg = (text or "").strip().lower()
    keys = ["不需要预约", "不用预约", "先不预约", "不约了", "取消当前预约", "退出预约"]
    return any(k in msg for k in keys)


def _query_labs(date_text: str, campus: str, lab_type: str, participant_count: Optional[int] = None) -> List[Laboratory]:
    labs = Laboratory.query.filter_by(status="active").order_by(Laboratory.id.asc()).all()
    if campus:
        labs = [lab for lab in labs if lab.campus and campus in (lab.campus.campus_name or "")]
    if lab_type:
        labs = [
            lab
            for lab in labs
            if (lab.description and lab_type.lower() in lab.description.lower())
            or (lab.lab_name and lab_type.lower() in lab.lab_name.lower())
        ]
    if participant_count:
        labs = [lab for lab in labs if (lab.capacity or 0) >= participant_count]
    if date_text:
        try:
            d = datetime.strptime(date_text, "%Y-%m-%d").date()
        except Exception:
            return []
        filtered = []
        for lab in labs:
            rows = get_lab_schedule(lab, d).get("reservations") or []
            if len(rows) < 12:
                filtered.append(lab)
        labs = filtered
    return labs


def _query_schedule(date_text: str, lab_id: Optional[int]) -> Dict[str, Any]:
    if not date_text:
        return {"ok": False, "message": "请先提供日期(YYYY-MM-DD)。"}
    try:
        d = datetime.strptime(date_text, "%Y-%m-%d").date()
    except Exception:
        return {"ok": False, "message": "日期格式不正确，请使用 YYYY-MM-DD。"}
    if lab_id:
        lab = Laboratory.query.get(lab_id)
        if not lab:
            return {"ok": False, "message": f"未找到实验室ID {lab_id}。"}
        return {"ok": True, "schedules": [{"lab": lab, "schedule": get_lab_schedule(lab, d)}]}
    labs = Laboratory.query.filter_by(status="active").order_by(Laboratory.id.asc()).limit(12).all()
    return {"ok": True, "schedules": [{"lab": lab, "schedule": get_lab_schedule(lab, d)} for lab in labs]}


def _recommend_time(date_text: str, lab_id: Optional[int], preference: str) -> Tuple[str, Optional[Dict[str, Any]]]:
    result = _query_schedule(date_text, lab_id)
    if not result.get("ok"):
        return result.get("message") or "无法查询排期。", None
    best, best_score = None, -1
    for item in result["schedules"]:
        lab, schedule = item["lab"], item["schedule"]
        open_m, close_m = _to_minutes(schedule["open_time"]), _to_minutes(schedule["close_time"])
        occupied = sorted([(_to_minutes(r["start_time"][:5]), _to_minutes(r["end_time"][:5])) for r in schedule.get("reservations") or []])
        free, cur = [], open_m
        for s, e in occupied:
            if s > cur:
                free.append((cur, s))
            cur = max(cur, e)
        if cur < close_m:
            free.append((cur, close_m))
        for s, e in free:
            dur = e - s
            if dur < 60:
                continue
            score = dur + (30 if "上午" in preference and s < 12 * 60 else 0) + (30 if "下午" in preference and s >= 12 * 60 else 0)
            if score > best_score:
                best_score = score
                best = {"lab_id": lab.id, "lab_name": lab.lab_name, "start": s, "end": min(s + 120, e)}
    if not best:
        return "当天没有合适的连续空闲时段。", None
    st = f"{best['start'] // 60:02d}:{best['start'] % 60:02d}"
    et = f"{best['end'] // 60:02d}:{best['end'] % 60:02d}"
    return f"我为你推荐: {date_text} {st}-{et}, 实验室 {best['lab_name']}。", {"date": date_text, "lab_id": best["lab_id"], "start_time": st, "end_time": et}


def _extract_form_from_text(user, text: str, form: Dict[str, Any], session: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(form)
    d = _detect_date(text)
    if d:
        merged["date"] = d
    st, et = _detect_time_range(text)
    if st:
        merged["start_time"] = st
    if et:
        merged["end_time"] = et
    c = _detect_participant_count(text)
    if c:
        merged["participant_count"] = c
    p = _detect_purpose(text)
    if p:
        merged["purpose"] = p
    campus = _detect_campus(text)
    if campus:
        merged["campus"] = campus
    t = _detect_type(text)
    if t:
        merged["type"] = t
    lab_id = _detect_lab_id_or_choice(text, session)
    if lab_id:
        merged["lab_id"] = lab_id
    merged = _llm_extract_form(text, merged)
    if not merged.get("participant_count"):
        merged["participant_count"] = 1
    return merged


def _normalize_chat_result(result: Any, trace_id: str = "") -> Dict[str, Any]:
    normalized = dict(result) if isinstance(result, dict) else {"reply": str(result or "")}
    normalized.setdefault("reply", "")
    actions = normalized.get("actions")
    if not isinstance(actions, list):
        actions = []
    if normalized.get("type") == "tool_call":
        tool = str(normalized.get("tool") or "")
        params = normalized.get("params") if isinstance(normalized.get("params"), dict) else {}
        if tool == "navigate" and params.get("path"):
            actions.append({"label": "前往页面", "path": params["path"]})
        if tool in {"my_reservations", "cancel_reservation"}:
            actions.append({"label": "查看我的预约", "path": "/pages/my-reservations/my-reservations"})
    normalized["actions"] = actions
    normalized["trace_id"] = str(normalized.get("trace_id") or trace_id or _new_trace_id())
    return normalized


def _llm_agent_decide(context: str, history: List[Dict[str, Any]], form: Dict[str, Any]) -> Dict[str, Any]:
    if not Config.LLM_API_KEY:
        return {}
    tools = [
        {"name": "query_labs", "required": [], "optional": ["date", "campus", "type", "participant_count"]},
        {"name": "query_schedule", "required": ["date"], "optional": ["lab_id"]},
        {"name": "recommend_time", "required": ["date"], "optional": ["lab_id", "preference"]},
        {"name": "create_reservation", "required": ["lab_id", "date", "start_time", "end_time", "participant_count", "purpose"], "optional": []},
        {"name": "my_reservations", "required": [], "optional": []},
        {"name": "cancel_reservation", "required": ["reservation_id"], "optional": []},
        {"name": "navigate", "required": ["path"], "optional": []},
    ]
    prompt = f"""
你是实验室预约 Agent 规划器。每次只能做一步:
1) 选择一个工具执行，或
2) done=true 并给最终答复。

规则:
{_rules_context()}

工具:
{json.dumps(tools, ensure_ascii=False)}

当前表单:
{json.dumps(form, ensure_ascii=False)}

历史:
{json.dumps(history[-6:], ensure_ascii=False)}

上下文:
{context}

仅输出JSON:
{{"tool":"工具名或空", "params":{{}}, "reply":"给用户的回复", "done":true/false}}
""".strip()
    try:
        content = _call_llm_messages(
            [
                {"role": "system", "content": "你是严格 JSON 输出助手。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
        )
        parsed = _safe_json_loads(content) or {}
        tool = str(parsed.get("tool") or "").strip()
        if tool and tool not in AGENT_TOOL_SCHEMAS:
            tool = ""
        return {
            "tool": tool,
            "params": _normalize_params_shape(parsed.get("params")),
            "reply": str(parsed.get("reply") or "").strip(),
            "done": bool(parsed.get("done", False)),
        }
    except Exception:
        return {}


def _labs_to_text(labs: List[Laboratory]) -> str:
    if not labs:
        return "没有找到符合条件的实验室。"
    lines = []
    for i, lab in enumerate(labs[:8], start=1):
        campus_name = getattr(lab.campus, "campus_name", "") if getattr(lab, "campus", None) else ""
        lines.append(f"{i}. ID={lab.id} | {lab.lab_name} | 容量={lab.capacity} | 校区={campus_name}")
    return "\n".join(lines)


def _schedule_result_to_text(result: Dict[str, Any]) -> str:
    if not result.get("ok"):
        return result.get("message", "查询排期失败。")
    parts = []
    for item in result.get("schedules", []):
        lab, schedule = item["lab"], item["schedule"]
        rows = schedule.get("reservations") or []
        row_text = [f"{r['start_time'][:5]}-{r['end_time'][:5]}({r.get('status', '')})" for r in rows[:10]]
        parts.append(
            f"LabID={lab.id} | {lab.lab_name} | 开放={schedule.get('open_time')}-{schedule.get('close_time')} | "
            f"预约={'; '.join(row_text) if row_text else '无'}"
        )
    return "\n".join(parts) if parts else "没有排期数据。"


def _normalize_nav_path(path: str) -> str:
    raw = str(path or "").strip()
    if not raw:
        return "/pages/agent/agent"
    mapping = {
        "/pages/my-reservations/index": "/pages/my-reservations/my-reservations",
        "/pages/agent/index": "/pages/agent/agent",
        "/pages/labs/index": "/pages/labs/labs",
        "/pages/reserve/index": "/pages/reserve/reserve",
        "/pages/schedule/index": "/pages/labs/labs",
    }
    return mapping.get(raw, raw)


def _auto_fill_params(tool: str, user, params: Dict[str, Any], form: Dict[str, Any], text: str, session: Dict[str, Any]) -> Dict[str, Any]:
    merged = _extract_form_from_text(user, text, form, session)
    raw = dict(params or {})
    for key in ["date", "participant_count", "start_time", "end_time", "purpose", "campus", "type", "lab_id"]:
        if not raw.get(key) and merged.get(key):
            raw[key] = merged[key]
    if tool == "cancel_reservation" and not raw.get("reservation_id"):
        rid = _detect_reservation_id_or_choice(text, session)
        if rid:
            raw["reservation_id"] = rid
    return _sanitize_tool_params(tool, raw)


def _run_tool(tool: str, params: Dict[str, Any], user, session: Dict[str, Any]) -> Dict[str, Any]:
    missing = _missing_required_tool_fields(tool, params)
    if missing:
        return _tool_result(tool, False, _missing_fields_hint(tool, missing), error_code="missing_fields", error_message="missing required params")
    if tool == "query_labs":
        labs = _query_labs(params.get("date") or "", params.get("campus") or "", params.get("type") or "", _safe_int(params.get("participant_count")))
        session["last_labs"] = [{"id": lab.id, "name": lab.lab_name} for lab in labs[:8]]
        return _tool_result(tool, True, _labs_to_text(labs), extra={"labs_count": len(labs)})
    if tool == "query_schedule":
        result = _query_schedule(params.get("date"), _safe_int(params.get("lab_id")))
        return _tool_result(tool, bool(result.get("ok")), _schedule_result_to_text(result), error_code="query_failed" if not result.get("ok") else "", raw=result)
    if tool == "recommend_time":
        reply, pick = _recommend_time(params.get("date"), _safe_int(params.get("lab_id")), str(params.get("preference") or ""))
        return _tool_result(tool, pick is not None, reply, error_code="no_slot" if pick is None else "", extra={"pick": pick})
    if tool == "create_reservation":
        payload = {
            "lab_id": _safe_int(params.get("lab_id")),
            "reservation_date": str(params.get("date") or ""),
            "start_time": str(params.get("start_time") or ""),
            "end_time": str(params.get("end_time") or ""),
            "participant_count": _safe_int(params.get("participant_count")) or 1,
            "purpose": str(params.get("purpose") or ""),
        }
        if not payload["lab_id"]:
            return _tool_result(tool, False, "缺少实验室ID，无法创建预约。", error_code="missing_fields")
        lab = Laboratory.query.get(int(payload["lab_id"]))
        if not lab:
            return _tool_result(tool, False, "未找到对应实验室。", error_code="not_found")
        payload["campus_id"] = lab.campus_id
        check_form = {
            "date": payload["reservation_date"],
            "start_time": payload["start_time"],
            "end_time": payload["end_time"],
            "participant_count": payload["participant_count"],
            "purpose": payload["purpose"],
            "lab_id": payload["lab_id"],
            "campus": "",
            "type": "",
        }
        min_days = _extract_min_advance_days(_rules_context())
        if min_days > 0:
            d = datetime.strptime(check_form["date"], "%Y-%m-%d").date()
            if d < _today() + timedelta(days=min_days):
                return _tool_result(tool, False, f"该预约不符合规则: 需至少提前 {min_days} 天预约。", error_code="business_rule")
        if _forbid_duplicate(_rules_context()):
            d = datetime.strptime(check_form["date"], "%Y-%m-%d").date()
            st = datetime.strptime(check_form["start_time"], "%H:%M").time()
            et = datetime.strptime(check_form["end_time"], "%H:%M").time()
            existed = Reservation.query.filter(
                Reservation.user_id == user.id,
                Reservation.reservation_date == d,
                Reservation.status.in_(ACTIVE_RESERVATION_STATUSES),
                Reservation.start_time < et,
                Reservation.end_time > st,
            ).first()
            if existed:
                return _tool_result(tool, False, "该预约不符合规则: 不允许重复预约冲突时间段。", error_code="business_rule")
        try:
            created = create_reservation(user, payload)
            _reset_form(session)
            return _tool_result(
                tool,
                True,
                f"{created.get('lab_name')}，{created.get('reservation_date')} {str(created.get('start_time'))[:5]}-{str(created.get('end_time'))[:5]}，状态={created.get('status')}",
                raw=created,
            )
        except AppError as exc:
            return _tool_result(tool, False, f"预约失败：{exc.message}", error_code="business_rule")
    if tool == "my_reservations":
        rows = (
            Reservation.query.filter_by(user_id=user.id)
            .order_by(Reservation.reservation_date.desc(), Reservation.start_time.desc())
            .limit(8)
            .all()
        )
        if not rows:
            session["last_reservations"] = []
            return _tool_result(tool, True, "你当前没有预约记录。")
        session["last_reservations"] = [{"id": row.id} for row in rows]
        lines = [f"{i}. ID={row.id} | {row.lab.lab_name if row.lab else '-'} | {row.reservation_date} {str(row.start_time)[:5]}-{str(row.end_time)[:5]} | {row.status}" for i, row in enumerate(rows, start=1)]
        return _tool_result(tool, True, "你的预约记录如下:\n" + "\n".join(lines))
    if tool == "cancel_reservation":
        reservation_id = _safe_int(params.get("reservation_id"))
        if not reservation_id:
            return _tool_result(tool, False, "缺少预约ID，无法取消。", error_code="missing_fields")
        reservation = Reservation.query.get(int(reservation_id))
        if not reservation:
            return _tool_result(tool, False, f"没有找到预约ID {reservation_id}。", error_code="not_found")
        try:
            updated = cancel_reservation(user, reservation)
            return _tool_result(tool, True, f"已取消预约 ID={updated.get('id')}，{updated.get('reservation_date')} {str(updated.get('start_time'))[:5]}-{str(updated.get('end_time'))[:5]}", raw=updated)
        except AppError as exc:
            return _tool_result(tool, False, f"取消失败：{exc.message}", error_code="business_rule")
    if tool == "navigate":
        return _tool_result(tool, True, _normalize_nav_path(str(params.get("path") or "")))
    return _tool_result(tool, False, f"未知工具：{tool}", error_code="unknown_tool")


def _fallback_rule_chat(user, text: str, session: Dict[str, Any]) -> Any:
    intent = _extract_intent(text)
    if intent == "cancel_flow" or _is_cancel_flow_message(text):
        _reset_form(session)
        return "好的，已退出当前预约流程。后续你可以继续让我查实验室、排期或帮你预约。"
    if intent == "query_labs":
        return _tool_call("query_labs", {}, "我来帮你查实验室。")
    if intent == "query_schedule":
        d = _detect_date(text)
        params = {"date": d} if d else {}
        return _tool_call("query_schedule", params, "我来帮你查排期。")
    if intent == "create_reservation":
        return _tool_call("create_reservation", {}, "我来帮你创建预约。")
    if intent == "my_reservations":
        return _tool_call("my_reservations", {}, "我帮你查询你的预约记录。")
    if intent == "cancel_reservation":
        rid = _detect_reservation_id_or_choice(text, session)
        params = {"reservation_id": rid} if rid else {}
        return _tool_call("cancel_reservation", params, "我来帮你取消该预约。")
    if intent == "recommend_time":
        d = _detect_date(text)
        params = {"date": d} if d else {}
        return _tool_call("recommend_time", params, "我帮你推荐时间。")
    if intent == "navigate":
        return _tool_call("navigate", {"path": "/pages/labs/labs"}, "我带你进入对应页面。")
    return _call_general_llm(user, text)


def _agent_loop(user, user_input: str, session: Dict[str, Any], trace_id: str) -> Any:
    if not Config.LLM_API_KEY:
        return _normalize_chat_result(_fallback_rule_chat(user, user_input, session), trace_id)
    context = user_input
    history: List[Dict[str, Any]] = []
    form = dict(session.get("reservation_form") or {})
    form = _extract_form_from_text(user, user_input, form, session)
    session["reservation_form"] = form
    last_tool, same_tool_count = "", 0
    for step in range(1, MAX_AGENT_STEPS + 1):
        decision = _llm_agent_decide(context, history, form)
        tool = str(decision.get("tool") or "").strip()
        params = _normalize_params_shape(decision.get("params"))
        planner_reply = str(decision.get("reply") or "").strip()
        done = bool(decision.get("done", False))
        if done and not tool:
            return {"reply": planner_reply or "处理完成。", "actions": [], "trace_id": trace_id}
        if not tool:
            return {"reply": planner_reply or "请补充更多信息。", "actions": [], "trace_id": trace_id}
        params = _auto_fill_params(tool, user, params, form, context, session)
        tool_result = _run_tool(tool, params, user, session)
        history.append(
            {
                "step": step,
                "tool": tool,
                "params": params,
                "ok": bool(tool_result.get("ok")),
                "result_summary": str(tool_result.get("data") or "")[:MAX_HISTORY_SUMMARY_CHARS],
                "error_code": tool_result.get("error_code"),
            }
        )
        same_tool_count = same_tool_count + 1 if tool == last_tool else 1
        last_tool = tool
        if same_tool_count > MAX_TOOL_REPEAT_STEPS:
            return {"reply": "同一步骤重复尝试过多次。请补充更具体信息后我再继续。", "actions": [], "trace_id": trace_id}
        if tool == "navigate":
            return {"reply": planner_reply or "我带你进入对应页面。", "actions": [{"label": "前往页面", "path": str(tool_result.get("data") or "/pages/agent/agent")}], "trace_id": trace_id}
        if tool in {"my_reservations", "cancel_reservation"}:
            return {"reply": str(tool_result.get("data") or "处理完成。"), "actions": [{"label": "查看我的预约", "path": "/pages/my-reservations/my-reservations"}], "trace_id": trace_id}
        if tool == "create_reservation":
            if tool_result.get("ok"):
                return {"reply": f"已帮你完成预约: {tool_result.get('data')}", "actions": [{"label": "查看我的预约", "path": "/pages/my-reservations/my-reservations"}], "trace_id": trace_id}
            return {"reply": str(tool_result.get("data") or "预约失败。"), "actions": [], "trace_id": trace_id}
        if done:
            return {"reply": planner_reply or str(tool_result.get("data") or "处理完成。"), "actions": [], "trace_id": trace_id}
        if not tool_result.get("ok") and tool_result.get("error_code") in {"missing_fields", "invalid_params", "not_found", "business_rule"}:
            return {"reply": str(tool_result.get("data") or "处理失败。"), "actions": [], "trace_id": trace_id}
        context = (
            f"USER_REQUEST: {user_input}\n"
            f"STEP: {step}\n"
            f"TOOL: {tool}\n"
            f"TOOL_PARAMS: {json.dumps(params, ensure_ascii=False)}\n"
            f"TOOL_OK: {tool_result.get('ok')}\n"
            f"TOOL_RESULT: {str(tool_result.get('data') or '')[:MAX_HISTORY_SUMMARY_CHARS]}\n"
            f"CURRENT_FORM: {json.dumps(form, ensure_ascii=False)}\n"
            "继续选择下一步。若已满足需求，请 done=true。"
        )
    return _normalize_chat_result(_fallback_rule_chat(user, user_input, session), trace_id)


def chat(user, message):
    text = str(message or "").strip()
    trace_id = _new_trace_id()
    if not text:
        return {"reply": "你可以让我查实验室、查排期、创建预约、取消预约，或查看我的预约。", "actions": [], "trace_id": trace_id}
    user_id = getattr(user, "id", None)
    if not user_id and isinstance(user, dict):
        user_id = user.get("id")
    if not user_id:
        return {"reply": "用户信息异常，暂时无法处理请求。", "actions": [], "trace_id": trace_id}
    session = _clean_session(user_id)
    try:
        if _is_cancel_flow_message(text):
            _reset_form(session)
            _save_session(user_id, session)
            return _normalize_chat_result("好的，已退出当前预约流程。后续你可以继续让我查实验室、排期或帮你预约。", trace_id)
        if not _is_lab_related(text):
            result = _call_general_llm(user, text)
            _save_session(user_id, session)
            return _normalize_chat_result(result, trace_id)
        try:
            result = _agent_loop(user, text, session, trace_id)
        except Exception:
            try:
                result = _fallback_rule_chat(user, text, session)
            except Exception:
                result = _call_general_llm(user, text)
        _save_session(user_id, session)
        return _normalize_chat_result(result, trace_id)
    except Exception as exc:
        return {"reply": f"系统处理失败: {str(exc)}", "actions": [], "trace_id": trace_id}

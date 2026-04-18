import json
import re
from datetime import date, datetime, time, timedelta
from typing import Any, Dict, List, Optional, Tuple

import requests

from app.config import Config
from app.models import Laboratory, Reservation
from app.services.reservation_service import create_reservation, get_lab_schedule
from app.utils.exceptions import AppError


ACTIVE_RESERVATION_STATUSES = {"pending", "approved"}
SESSION_TTL_MINUTES = 30

AGENT_SESSIONS: Dict[int, Dict[str, Any]] = {}


def _now() -> datetime:
    return datetime.now()


def _today() -> date:
    return date.today()


def _tool_call(tool: str, params: Dict[str, Any], reply: str) -> Dict[str, Any]:
    return {"type": "tool_call", "tool": tool, "params": params, "reply": reply}


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


def _rules_context() -> str:
    text = str(getattr(Config, "AGENT_RULES_CONTEXT", "") or "")
    if text.strip():
        return text
    return (
        "实验室规则：预约必须遵守实验室开放时间与容量限制；"
        "预约需满足系统时间规则（至少提前30分钟，且不超过未来7天）；"
        "学生和教师预约默认需要审批；"
        "若用户人数超过实验室容量，则不允许预约；"
        "若用户已有冲突时间段预约，则不允许重复预约。"
    )


def _extract_min_advance_days(ctx: str) -> int:
    if "至少提前一天" in ctx or "至少提前1天" in ctx:
        return 1
    m = re.search(r"至少提前\s*(\d+)\s*(?:天|日)", ctx)
    if m:
        return int(m.group(1))
    return 0


def _forbid_duplicate(ctx: str) -> bool:
    return "不允许重复预约" in ctx or "禁止重复预约" in ctx


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
            dt = date(today.year, int(m2.group(1)), int(m2.group(2)))
            return dt.isoformat()
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
        r"(上午|下午|晚上|中午)?\s*(\d{1,2})点(?:(\d{1,2})分|(半))?\s*(?:-|到|至)\s*"
        r"(上午|下午|晚上|中午)?\s*(\d{1,2})点(?:(\d{1,2})分|(半))?",
        msg,
    )
    if m2:
        p1, h1, m1, half1, p2, h2, m2_, half2 = m2.groups()
        mm1 = 30 if half1 else int(m1 or 0)
        mm2 = 30 if half2 else int(m2_ or 0)
        return _normalize_clock(int(h1), mm1, p1), _normalize_clock(int(h2), mm2, p2)

    single = re.search(r"(上午|下午|晚上|中午)\s*(\d{1,2})点", msg)
    if single:
        period, h = single.groups()
        start = _normalize_clock(int(h), 0, period)
        sh, sm = [int(i) for i in start.split(":")]
        end_dt = datetime.combine(_today(), time(hour=sh, minute=sm)) + timedelta(hours=2)
        return start, end_dt.strftime("%H:%M")

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
    if any(k in msg for k in ["实验", "课程", "调试", "讨论", "答辩", "培训", "会议", "上课", "学习"]):
        return msg[:120]
    return None


def _detect_campus(text: str) -> str:
    msg = text or ""
    for key in ["海淀", "朝阳", "通州", "新区", "校本部", "校区"]:
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


def _to_minutes(hhmm: str) -> int:
    h, m = [int(i) for i in hhmm.split(":")]
    return h * 60 + m


def _safe_json_loads(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    text = text.strip()

    # 去掉 ```json ... ```
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text.strip(), flags=re.IGNORECASE).strip()
        text = re.sub(r"```$", "", text.strip()).strip()

    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    m = re.search(r"(\{.*\})", text, re.DOTALL)
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
        raise RuntimeError("缺少 LLM_API_KEY")

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


def _llm_extract_intent(text: str) -> Optional[str]:
    if not Config.LLM_API_KEY:
        return None

    prompt = f"""
你是意图识别助手。请从下面类别中选择一个最合适的：
- query_labs
- query_schedule
- create_reservation
- my_reservations
- recommend_time
- navigate
- general

用户输入：
{text}

只返回 JSON：
{{"intent":"xxx"}}
""".strip()

    try:
        content = _call_llm_messages(
            [
                {"role": "system", "content": "你是一个严格输出 JSON 的意图识别助手。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
        )
        parsed = _safe_json_loads(content) or {}
        intent = parsed.get("intent")
        if intent in {
            "query_labs",
            "query_schedule",
            "create_reservation",
            "my_reservations",
            "recommend_time",
            "navigate",
            "general",
        }:
            return intent
    except Exception:
        return None

    return None


def _llm_extract_form(text: str, form: Dict[str, Any]) -> Dict[str, Any]:
    """
    用大模型提取表单字段，作为规则解析的增强补充。
    """
    if not Config.LLM_API_KEY:
        return form

    today = _today().isoformat()

    prompt = f"""
你是一个实验室预约信息抽取助手。
今天日期是：{today}

请从用户输入中提取以下字段，并返回 JSON：
- date: YYYY-MM-DD，没有就返回空字符串
- start_time: HH:MM，没有就返回空字符串
- end_time: HH:MM，没有就返回空字符串
- participant_count: 整数，没有就返回 null
- purpose: 字符串，没有就返回空字符串
- campus: 字符串，没有就返回空字符串
- type: 字符串，没有就返回空字符串
- lab_id: 整数，没有就返回 null

要求：
1. 只能输出 JSON，不要解释
2. “明天/后天/今天”要转成具体日期
3. “上午九点到十一点”这类表达要转成 24 小时制
4. 如果只有“上午九点”，可以只提取 start_time，不要瞎补 end_time
5. 如果信息不存在，返回空字符串或 null

已有表单：
{json.dumps(form, ensure_ascii=False)}

用户输入：
{text}
""".strip()

    try:
        content = _call_llm_messages(
            [
                {"role": "system", "content": "你是一个严格输出 JSON 的信息抽取助手。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
        )
        parsed = _safe_json_loads(content) or {}

        for k in ["date", "start_time", "end_time", "purpose", "campus", "type"]:
            if parsed.get(k):
                form[k] = parsed[k]

        if parsed.get("participant_count") is not None:
            try:
                form["participant_count"] = int(parsed["participant_count"])
            except Exception:
                pass

        if parsed.get("lab_id") is not None:
            try:
                form["lab_id"] = int(parsed["lab_id"])
            except Exception:
                pass

    except Exception:
        pass

    return form


def _extract_intent(text: str) -> str:
    msg = (text or "").strip().lower()

    if any(k in msg for k in ["去预约页面", "去排期页面", "跳转", "打开页面", "进入页面"]):
        return "navigate"
    if any(k in msg for k in ["我的预约", "我有哪些预约", "预约列表"]):
        return "my_reservations"
    if any(k in msg for k in ["推荐时间", "什么时候有空", "什么时候空", "帮我推荐时间", "推荐个时间"]):
        return "recommend_time"
    if any(k in msg for k in ["排期", "有没有空", "是否空闲", "schedule"]):
        return "query_schedule"
    if any(k in msg for k in ["预约", "预定"]):
        return "create_reservation"
    if any(k in msg for k in ["有哪些实验室", "查询实验室", "可用实验室", "空闲实验室"]):
        return "query_labs"
    if any(k in msg for k in ["实验室", "lab"]):
        return "query_labs"

    llm_intent = _llm_extract_intent(text)
    if llm_intent:
        return llm_intent

    return "general"


def _is_lab_related(text: str) -> bool:
    msg = (text or "").lower()
    keys = ["实验室", "预约", "排期", "空闲", "lab", "schedule", "reservation", "校区", "设备"]
    return any(k in msg for k in keys)


def _call_general_llm(user, message: str) -> str:
    if Config.AGENT_PROVIDER not in {"openai", "deepseek", "llm"} or not Config.LLM_API_KEY:
        return "我当前可以优先帮你处理实验室相关问题。"

    try:
        return _call_llm_messages(
            [
                {"role": "system", "content": "你是一个通用中文助手，请简洁、自然地回答用户问题。"},
                {"role": "user", "content": message},
            ],
            temperature=0.3,
        )
    except requests.exceptions.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else None
        if status == 401:
            return "通用模型鉴权失败（401），请检查 LLM_API_KEY 是否正确。"
        if status == 403:
            return "通用模型请求被拒绝（403），请检查账号权限、IP 白名单或服务策略。"
        if status == 429:
            return "通用模型请求过于频繁（429），请稍后再试。"
        if status and status >= 500:
            return f"通用模型服务暂时异常（{status}），请稍后重试。"
        return f"通用模型调用失败（HTTP {status or 'unknown'}）。"
    except requests.exceptions.Timeout:
        return "通用模型请求超时，请检查网络后重试。"
    except requests.exceptions.ConnectionError as exc:
        detail = str(exc)
        if "10013" in detail:
            return "通用模型网络连接被系统拦截（WinError 10013），请检查防火墙/代理/安全软件放行 443 出站。"
        return "无法连接通用模型网络，请检查服务器网络或代理设置。"
    except Exception:
        return "我暂时无法连接通用模型，请稍后重试。"


def _query_labs(
    date_text: str,
    campus: str,
    lab_type: str,
    participant_count: Optional[int] = None,
) -> List[Laboratory]:
    q = Laboratory.query.filter_by(status="active")
    labs = q.order_by(Laboratory.id.asc()).all()

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
        d = datetime.strptime(date_text, "%Y-%m-%d").date()
        filtered: List[Laboratory] = []
        for lab in labs:
            rows = get_lab_schedule(lab, d).get("reservations") or []
            total = len(rows)
            if total >= 12:
                continue
            filtered.append(lab)
        labs = filtered

    return labs


def _query_schedule(date_text: str, lab_id: Optional[int]) -> Dict[str, Any]:
    if not date_text:
        return {"ok": False, "message": "请先提供日期（YYYY-MM-DD）。"}

    try:
        d = datetime.strptime(date_text, "%Y-%m-%d").date()
    except Exception:
        return {"ok": False, "message": "日期格式不正确，请使用 YYYY-MM-DD。"}

    if lab_id:
        lab = Laboratory.query.get(lab_id)
        if not lab:
            return {"ok": False, "message": f"未找到实验室ID {lab_id}。"}
        schedule = get_lab_schedule(lab, d)
        return {"ok": True, "schedules": [{"lab": lab, "schedule": schedule}]}

    labs = Laboratory.query.filter_by(status="active").order_by(Laboratory.id.asc()).limit(12).all()
    return {
        "ok": True,
        "schedules": [{"lab": lab, "schedule": get_lab_schedule(lab, d)} for lab in labs],
    }


def _recommend_time(date_text: str, lab_id: Optional[int], preference: str) -> Tuple[str, Optional[Dict[str, Any]]]:
    result = _query_schedule(date_text, lab_id)
    if not result.get("ok"):
        return result.get("message") or "无法查询排期。", None

    best = None
    best_score = -1

    for item in result["schedules"]:
        lab: Laboratory = item["lab"]
        schedule = item["schedule"]

        open_m = _to_minutes(schedule["open_time"])
        close_m = _to_minutes(schedule["close_time"])
        rows = schedule.get("reservations") or []

        occupied: List[Tuple[int, int]] = []
        for r in rows:
            occupied.append((_to_minutes(r["start_time"][:5]), _to_minutes(r["end_time"][:5])))
        occupied.sort()

        free: List[Tuple[int, int]] = []
        cur = open_m
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

            score = dur
            if "上午" in preference and s < 12 * 60:
                score += 30
            if "下午" in preference and s >= 12 * 60:
                score += 30

            if score > best_score:
                best_score = score
                best = {
                    "lab_id": lab.id,
                    "lab_name": lab.lab_name,
                    "start": s,
                    "end": min(s + 120, e),
                }

    if not best:
        return "当天没有合适的连续空闲时段。", None

    st = f"{best['start']//60:02d}:{best['start']%60:02d}"
    et = f"{best['end']//60:02d}:{best['end']%60:02d}"
    reply = f"我帮你推荐了较优时段：{date_text} {st}-{et}，实验室 {best['lab_name']}（冲突少且连续空闲更长）。"
    return reply, {
        "date": date_text,
        "lab_id": best["lab_id"],
        "start_time": st,
        "end_time": et,
    }


def _apply_context_rules(user, form: Dict[str, Any], lab: Laboratory) -> Optional[str]:
    ctx = _rules_context()

    # 先做 LLM 规则判断（增强）
    if Config.LLM_API_KEY:
        try:
            prompt = f"""
你是实验室预约规则检查助手。

实验室规则：
{ctx}

实验室信息：
- 名称：{lab.lab_name}
- 容量：{lab.capacity}
- 开放时间：{getattr(lab, "open_time", "")}
- 关闭时间：{getattr(lab, "close_time", "")}

用户预约表单：
{json.dumps(form, ensure_ascii=False)}

请判断该预约是否违规：
- 如果不违规，只返回：OK
- 如果违规，只返回一句简短中文原因
不要输出其他内容。
""".strip()

            content = _call_llm_messages(
                [
                    {"role": "system", "content": "你是一个严格规则检查助手。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
            )

            if content.strip() and content.strip().upper() != "OK":
                return content.strip()
        except Exception:
            pass

    # 规则：至少提前 N 天
    min_days = _extract_min_advance_days(ctx)
    if min_days > 0:
        d = datetime.strptime(form["date"], "%Y-%m-%d").date()
        if d < _today() + timedelta(days=min_days):
            return f"该预约不符合规则：需至少提前 {min_days} 天预约。"

    # 规则：容量限制
    if form["participant_count"] and int(form["participant_count"]) > (lab.capacity or 0):
        return f"该预约不符合规则：人数超过实验室容量上限（{lab.capacity}）。"

    # 规则：不允许重复预约
    if _forbid_duplicate(ctx):
        d = datetime.strptime(form["date"], "%Y-%m-%d").date()
        st = datetime.strptime(form["start_time"], "%H:%M").time()
        et = datetime.strptime(form["end_time"], "%H:%M").time()
        existed = Reservation.query.filter(
            Reservation.user_id == user.id,
            Reservation.reservation_date == d,
            Reservation.status.in_(ACTIVE_RESERVATION_STATUSES),
            Reservation.start_time < et,
            Reservation.end_time > st,
        ).first()
        if existed:
            return "该预约不符合规则：不允许重复预约冲突时间段。"

    return None


def _pick_lab_for_form(form: Dict[str, Any]) -> Optional[Laboratory]:
    if form.get("lab_id"):
        return Laboratory.query.get(int(form["lab_id"]))

    labs = _query_labs(
        date_text=form["date"],
        campus=form.get("campus") or "",
        lab_type=form.get("type") or "",
        participant_count=int(form["participant_count"]) if form.get("participant_count") else None,
    )
    if not labs:
        return None
    return labs[0]


def _extract_form_from_text(user, text: str, form: Dict[str, Any], session: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(form)

    # 第一层：规则解析（稳定）
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

    # 第二层：LLM 解析增强
    merged = _llm_extract_form(text, merged)

    if not merged.get("participant_count"):
        merged["participant_count"] = 1

    return merged


def _missing_create_fields(form: Dict[str, Any]) -> List[str]:
    missing = []
    if not form.get("date"):
        missing.append("预约日期")
    if not form.get("start_time"):
        missing.append("开始时间")
    if not form.get("end_time"):
        missing.append("结束时间")
    if not form.get("participant_count"):
        missing.append("参与人数")
    if not form.get("purpose"):
        missing.append("使用目的")
    return missing


def _handle_query_labs(user, text: str, session: Dict[str, Any]) -> Dict[str, Any]:
    form = _extract_form_from_text(user, text, session["reservation_form"], session)
    session["reservation_form"] = form

    labs = _query_labs(
        form.get("date") or "",
        form.get("campus") or "",
        form.get("type") or "",
        form.get("participant_count"),
    )

    session["last_labs"] = [{"id": lab.id, "name": lab.lab_name} for lab in labs[:5]]

    params = {}
    if form.get("date"):
        params["date"] = form["date"]
    if form.get("campus"):
        params["campus"] = form["campus"]
    if form.get("type"):
        params["type"] = form["type"]

    if not labs:
        return _tool_call("query_labs", params, "当前条件下没有找到合适实验室，你可以换个日期或校区。")

    lines = [f"{i+1}. {lab.lab_name}（容量{lab.capacity}）" for i, lab in enumerate(labs[:5])]
    return _tool_call("query_labs", params, "我帮你查到了这些实验室：\n" + "\n".join(lines))


def _handle_query_schedule(user, text: str, session: Dict[str, Any]) -> Any:
    form = _extract_form_from_text(user, text, session["reservation_form"], session)
    session["reservation_form"] = form

    if not form.get("date"):
        return "请告诉我日期，我再帮你查排期，例如：明天、后天，或者 2026-04-20。"

    params = {"date": form["date"]}
    if form.get("lab_id"):
        params["lab_id"] = int(form["lab_id"])

    return _tool_call("query_schedule", params, "我帮你查询该日期排期。")


def _handle_recommend_time(user, text: str, session: Dict[str, Any]) -> Any:
    form = _extract_form_from_text(user, text, session["reservation_form"], session)
    session["reservation_form"] = form

    if not form.get("date"):
        return "你希望我推荐哪一天的时间？"

    preference = "上午" if "上午" in text else ("下午" if "下午" in text else "")
    reply, pick = _recommend_time(form["date"], form.get("lab_id"), preference)

    if not pick:
        return reply

    params = {"date": pick["date"], "lab_id": pick["lab_id"]}

    form["lab_id"] = pick["lab_id"]
    form["start_time"] = pick["start_time"]
    form["end_time"] = pick["end_time"]
    session["reservation_form"] = form

    return _tool_call("query_schedule", params, reply)


def _handle_my_reservations(user) -> Dict[str, Any]:
    return _tool_call("my_reservations", {}, "我帮你查询你的预约记录。")


def _handle_navigate(text: str) -> Dict[str, Any]:
    path = "/pages/agent/agent"
    msg = text or ""

    if "我的预约" in msg:
        path = "/pages/my-reservations/my-reservations"
    elif "排期" in msg:
        path = "/pages/schedule/index"
    elif "预约" in msg or "实验室" in msg:
        path = "/pages/labs/labs"

    return _tool_call("navigate", {"path": path}, "我带你进入对应页面。")


def _handle_create_reservation(user, text: str, session: Dict[str, Any]) -> Any:
    form = _extract_form_from_text(user, text, session["reservation_form"], session)
    session["reservation_form"] = form

    missing = _missing_create_fields(form)
    if missing:
        labels = "、".join(missing)
        return f"还缺少这些信息：{labels}。你可以直接告诉我，例如“明天上午9点到11点，3人，用于课程实验”。"

    # 时间合法性检查
    try:
        st = datetime.strptime(form["start_time"], "%H:%M")
        et = datetime.strptime(form["end_time"], "%H:%M")
        if et <= st:
            return "结束时间需要晚于开始时间，请重新告诉我时间段。"
    except Exception:
        return "时间格式有误，请按“09:00-11:00”或“上午9点到11点”这种方式告诉我。"

    lab = _pick_lab_for_form(form)
    if not lab:
        params = {"date": form["date"]}
        if form.get("campus"):
            params["campus"] = form["campus"]
        if form.get("type"):
            params["type"] = form["type"]
        return _tool_call("query_labs", params, "我先帮你筛选可预约实验室，请选择一个实验室后我继续创建预约。")

    violated = _apply_context_rules(user, form, lab)
    if violated:
        return violated

    payload = {
        "campus_id": lab.campus_id,
        "lab_id": lab.id,
        "reservation_date": form["date"],
        "start_time": form["start_time"],
        "end_time": form["end_time"],
        "participant_count": form["participant_count"],
        "purpose": form["purpose"],
    }

    try:
        created = create_reservation(user, payload)
        params = {
            "date": form["date"],
            "start_time": form["start_time"],
            "end_time": form["end_time"],
            "participant_count": form["participant_count"],
            "purpose": form["purpose"],
            "lab_id": lab.id,
        }
        _reset_form(session)
        return _tool_call(
            "create_reservation",
            params,
            f"预约已创建成功：{created.get('lab_name')}，{created.get('reservation_date')} "
            f"{str(created.get('start_time'))[:5]}-{str(created.get('end_time'))[:5]}，状态 {created.get('status')}。",
        )
    except AppError as exc:
        return f"预约失败：{exc.message}"


def _normalize_chat_result(result: Any) -> Dict[str, Any]:
    if isinstance(result, dict):
        normalized = dict(result)
        normalized.setdefault("reply", "")
        normalized.setdefault("actions", [])

        if normalized.get("type") == "tool_call":
            tool = normalized.get("tool")
            params = normalized.get("params") or {}
            actions = normalized.get("actions") or []

            if tool == "navigate" and params.get("path"):
                actions.append({"label": "前往页面", "path": params["path"]})

            normalized["actions"] = actions

        return normalized

    return {"reply": str(result or ""), "actions": []}


def chat(user, message):
    text = str(message or "").strip()

    if not text:
        return {
            "reply": "你可以告诉我：想查实验室、查排期、创建预约，或者问我一个普通问题。",
            "actions": [],
        }

    user_id = getattr(user, "id", None)
    if not user_id and isinstance(user, dict):
        user_id = user.get("id")

    session = _clean_session(user_id)

    intent = _extract_intent(text)

    form = session["reservation_form"]

    # 多轮补全
    if any(form.get(k) for k in ["date", "start_time", "end_time", "purpose", "lab_id"]):
        if _is_lab_related(text):
            if intent in {"general", "query_labs", "query_schedule"}:
                intent = "create_reservation"

    # 分发逻辑（这一块最容易写错🔥）
    if intent == "query_labs":
        result = _handle_query_labs(user, text, session)

    elif intent == "query_schedule":
        result = _handle_query_schedule(user, text, session)

    elif intent == "create_reservation":
        result = _handle_create_reservation(user, text, session)

    elif intent == "my_reservations":
        result = _handle_my_reservations(user)

    elif intent == "recommend_time":
        result = _handle_recommend_time(user, text, session)

    elif intent == "navigate":
        result = _handle_navigate(text)

    else:
        result = _call_general_llm(user, text)

    _save_session(user_id, session)

    return _normalize_chat_result(result)
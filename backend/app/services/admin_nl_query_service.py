import json
import re
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

import requests

from app.config import Config
from app.services.asset_service import list_asset_requests, list_assets
from app.services.lab_report_service import list_daily_reports
from app.utils.exceptions import AppError

DEFAULT_LIMIT = 200
MAX_LIMIT = 500
META_FLAG = "__META__="


def query_admin_data(
    current_user,
    domain: str,
    message: str,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    normalized_domain = str(domain or "").strip().lower()
    if normalized_domain not in {"daily_reports", "assets"}:
        raise AppError("domain only supports daily_reports or assets", 400, 40098)

    ctx = context or {}
    plan = _plan_query(normalized_domain, message, ctx)
    if normalized_domain == "daily_reports":
        return _query_daily_reports(current_user, plan)
    return _query_assets(current_user, plan, ctx)


def _query_daily_reports(current_user, plan: Dict[str, Any]) -> Dict[str, Any]:
    filters = plan.get("filters") or {}
    service_filters: Dict[str, Any] = {}

    status = _normalize_request_status(filters.get("status"))
    report_date = _normalize_date(filters.get("report_date"))
    time_scope = str(filters.get("time_scope") or "").strip().lower()
    campus_id = _safe_int(filters.get("campus_id"))
    campus_name = str(filters.get("campus_name") or "").strip()
    lab_name = str(filters.get("lab_name") or "").strip()
    limit = _normalize_limit(filters.get("limit"))

    if status:
        service_filters["status"] = status
    if report_date:
        service_filters["report_date"] = report_date
    if campus_id and campus_id > 0:
        service_filters["campus_id"] = campus_id

    rows = list_daily_reports(current_user, service_filters)
    start_date, end_date = _resolve_daily_date_range(filters)
    if start_date and end_date:
        rows = [row for row in rows if _is_row_in_date_range(row, start_date, end_date)]
        service_filters["report_date_start"] = start_date.isoformat()
        service_filters["report_date_end"] = end_date.isoformat()

    rows = _filter_daily_rows(rows, filters)
    total = len(rows)
    rows = rows[:limit]

    return {
        "reply": _build_reply(plan.get("reply"), total, "日报"),
        "filters": {
            "status": status or "",
            "report_date": report_date or "",
            "time_scope": time_scope,
            "campus_name": campus_name,
            "lab_name": lab_name,
            "keyword": str(filters.get("keyword") or "").strip(),
            "campus_id": campus_id or "",
        },
        "items": rows,
        "meta": {
            "domain": "daily_reports",
            "total": total,
            "limit": limit,
            "applied_filters": service_filters,
        },
    }


def _query_assets(current_user, plan: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    filters = plan.get("filters") or {}
    mode_hint = str((plan.get("mode") or context.get("mode") or "")).strip().lower()
    mode = mode_hint if mode_hint in {"requests", "assets"} else "requests"
    limit = _normalize_limit(filters.get("limit"))
    campus_id = _safe_int(filters.get("campus_id"))

    if mode == "assets":
        status = _normalize_asset_status(filters.get("asset_status") or filters.get("status"))
        category = str(filters.get("category") or "").strip()
        service_filters: Dict[str, Any] = {}
        if status:
            service_filters["status"] = status
        if category:
            service_filters["category"] = category
        if campus_id and campus_id > 0:
            service_filters["campus_id"] = campus_id

        rows = list_assets(current_user, service_filters)
        rows = _filter_asset_rows(rows, filters)
        total = len(rows)
        rows = rows[:limit]
        return {
            "reply": _build_reply(plan.get("reply"), total, "资产台账"),
            "filters": {
                "panel_mode": "assets",
                "status": status or "",
                "category": category,
                "keyword": str(filters.get("keyword") or "").strip(),
                "campus_id": campus_id or "",
            },
            "items": rows,
            "meta": {
                "domain": "assets",
                "mode": "assets",
                "total": total,
                "limit": limit,
                "applied_filters": service_filters,
            },
        }

    status = _normalize_request_status(filters.get("status"))
    category = str(filters.get("category") or "").strip()
    service_filters: Dict[str, Any] = {}
    if status:
        service_filters["status"] = status
    if campus_id and campus_id > 0:
        service_filters["campus_id"] = campus_id

    rows = list_asset_requests(current_user, service_filters)
    rows = _filter_request_rows(rows, filters, category)
    total = len(rows)
    rows = rows[:limit]
    return {
        "reply": _build_reply(plan.get("reply"), total, "资产申报"),
        "filters": {
            "panel_mode": "requests",
            "status": status or "",
            "category": category,
            "keyword": str(filters.get("keyword") or "").strip(),
            "campus_id": campus_id or "",
        },
        "items": rows,
        "meta": {
            "domain": "assets",
            "mode": "requests",
            "total": total,
            "limit": limit,
            "applied_filters": service_filters,
        },
    }


def _plan_query(domain: str, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
    fallback = _fallback_plan(domain, message, context)
    if not _llm_enabled():
        return fallback
    try:
        planned = _plan_with_llm(domain, message, context)
        if not isinstance(planned, dict):
            return fallback

        fallback_filters = _compact_filters(fallback.get("filters") or {})
        planned_filters = _compact_filters(planned.get("filters") or {})
        merged_filters = dict(fallback_filters)
        # fallback fields are deterministic; llm only fills missing fields
        for key, value in planned_filters.items():
            if key not in merged_filters or _is_blank_filter_value(merged_filters.get(key)):
                merged_filters[key] = value
        if domain == "daily_reports":
            merged_filters = _sanitize_daily_merged_filters(merged_filters, message)

        return {
            "mode": planned.get("mode") or fallback.get("mode", ""),
            "filters": merged_filters,
            "reply": str(planned.get("reply") or "").strip(),
        }
    except Exception:
        return fallback


def _plan_with_llm(domain: str, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
    system_prompt = (
        "You are an admin-query parser. Output JSON only, no prose. "
        "Schema: {\"mode\":\"\", \"filters\":{}, \"reply\":\"\"}. "
        "For domain=daily_reports: mode empty; filters keys: "
        "status, report_date, time_scope, campus_id, campus_name, lab_name, reporter_name, keyword, limit. "
        "For domain=assets: mode in [requests, assets]. "
        "requests filters: status, category, campus_id, keyword, limit. "
        "assets filters: asset_status, category, campus_id, keyword, limit. "
        "status in [pending, approved, rejected]. asset_status in [in_use, spare, repair]. "
        "time_scope in [this_week, last_week, recent_3_days]. report_date in YYYY-MM-DD."
    )
    user_prompt = json.dumps(
        {"domain": domain, "context": context or {}, "message": str(message or "").strip()},
        ensure_ascii=False,
    )
    text = _call_llm_chat(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    )
    parsed = _extract_json(text)
    return parsed if isinstance(parsed, dict) else {}


def _call_llm_chat(messages: List[Dict[str, str]]) -> str:
    payload = {"model": Config.AGENT_MODEL, "messages": messages, "temperature": 0.1}
    headers = {"Authorization": f"Bearer {Config.LLM_API_KEY}", "Content-Type": "application/json"}
    resp = requests.post(Config.LLM_BASE_URL, headers=headers, json=payload, timeout=40)
    resp.raise_for_status()
    body = resp.json()
    choices = body.get("choices") or []
    if not choices:
        raise RuntimeError("llm response missing choices")
    content = ((choices[0] or {}).get("message") or {}).get("content")
    if content is None:
        raise RuntimeError("llm response missing content")
    return str(content).strip()


def _extract_json(text: str) -> Dict[str, Any]:
    raw = str(text or "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    m = re.search(r"\{[\s\S]*\}", raw)
    if not m:
        return {}
    try:
        parsed = json.loads(m.group(0))
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _fallback_plan(domain: str, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
    text = str(message or "").strip()
    lowered = text.lower()
    filters: Dict[str, Any] = {}
    mode = ""

    if domain == "assets":
        if _contains_any(text, ["\u5165\u5e93", "\u53f0\u8d26", "\u8d44\u4ea7\u7f16\u7801", "\u5382\u5bb6", "\u89c4\u683c"]):
            mode = "assets"
        elif _contains_any(text, ["\u7533\u62a5", "\u5ba1\u6279", "\u7533\u8bf7\u5355", "\u7533\u8bf7\u8bb0\u5f55"]):
            mode = "requests"
        else:
            mode = str(context.get("mode") or "requests").strip().lower()
            if mode not in {"requests", "assets"}:
                mode = "requests"

    if domain == "daily_reports":
        status = _normalize_request_status(_detect_status_token(text))
        report_date = _detect_date(text)
        time_scope = _detect_time_scope(text)
        campus_name = _detect_campus_keyword(text)
        lab_name = _detect_lab_keyword(text)
        if status:
            filters["status"] = status
        if report_date:
            filters["report_date"] = report_date
        if time_scope:
            filters["time_scope"] = time_scope
        if campus_name:
            filters["campus_name"] = campus_name
        if lab_name:
            filters["lab_name"] = lab_name
    elif mode == "requests":
        status = _normalize_request_status(_detect_status_token(text))
        if status:
            filters["status"] = status
        category = _extract_after_keyword(text, ["\u5206\u7c7b", "\u7c7b\u522b"])
        if category:
            filters["category"] = category
    else:
        status = _normalize_asset_status(_detect_asset_status_token(text))
        if status:
            filters["asset_status"] = status
        category = _extract_after_keyword(text, ["\u5206\u7c7b", "\u7c7b\u522b"])
        if category:
            filters["category"] = category

    keyword = _extract_quoted_keyword(text) or _extract_keyword_from_sentence(text, lowered)
    if keyword:
        filters["keyword"] = keyword

    return {"mode": mode, "filters": filters, "reply": ""}


def _detect_status_token(text: str) -> str:
    src = str(text or "").lower()
    if any(token in src for token in ["\u5f85\u5ba1\u6838", "\u5f85\u5ba1\u6279", "pending"]):
        return "pending"
    if any(token in src for token in ["\u5df2\u901a\u8fc7", "\u901a\u8fc7", "approved"]):
        return "approved"
    if any(token in src for token in ["\u5df2\u9a73\u56de", "\u9a73\u56de", "\u99c1\u56de", "rejected"]):
        return "rejected"
    return ""


def _detect_asset_status_token(text: str) -> str:
    src = str(text or "").lower()
    if any(token in src for token in ["\u5728\u7528", "\u4f7f\u7528\u4e2d", "in_use"]):
        return "in_use"
    if any(token in src for token in ["\u5907\u7528", "spare"]):
        return "spare"
    if any(token in src for token in ["\u7ef4\u4fee", "\u7ef4\u4fee\u4e2d", "repair"]):
        return "repair"
    return ""


def _detect_date(text: str) -> str:
    today = date.today()
    src = text or ""

    m_cn = re.search(r"(\d{1,2})\u6708(\d{1,2})\u65e5", src)
    if m_cn:
        return _safe_iso_date(today.year, int(m_cn.group(1)), int(m_cn.group(2)))

    m_ymd = re.search(r"(20\d{2})[-/.年](\d{1,2})[-/.月](\d{1,2})", src)
    if m_ymd:
        return _safe_iso_date(int(m_ymd.group(1)), int(m_ymd.group(2)), int(m_ymd.group(3)))

    m_md = re.search(r"(?<!\d)(\d{1,2})[-/.](\d{1,2})(?!\d)", src)
    if m_md:
        return _safe_iso_date(today.year, int(m_md.group(1)), int(m_md.group(2)))

    if "\u4eca\u5929" in src:
        return today.isoformat()
    if "\u6628\u5929" in src:
        return (today - timedelta(days=1)).isoformat()
    if "\u524d\u5929" in src:
        return (today - timedelta(days=2)).isoformat()
    return ""


def _detect_time_scope(text: str) -> str:
    src = str(text or "").lower()
    if any(token in src for token in ["\u672c\u5468", "\u8fd9\u5468", "\u672c\u661f\u671f", "\u8fd9\u661f\u671f", "this week"]):
        return "this_week"
    if any(token in src for token in ["\u4e0a\u5468", "\u4e0a\u661f\u671f", "last week"]):
        return "last_week"
    if any(token in src for token in ["\u6700\u8fd1\u4e09\u5929", "\u8fd1\u4e09\u5929", "\u6700\u8fd13\u5929", "\u8fd13\u5929", "last 3 days", "recent 3 days"]):
        return "recent_3_days"
    return ""


def _detect_campus_keyword(text: str) -> str:
    src = str(text or "").strip()
    if not src:
        return ""
    if any(token in src for token in ["\u6d77\u6dc0", "\u6d77\u6dc0\u6821\u533a"]):
        return "\u6d77\u6dc0"
    if any(token in src for token in ["\u4e30\u53f0", "\u4e30\u53f0\u6821\u533a"]):
        return "\u4e30\u53f0"
    if any(token in src for token in ["\u6d77\u5357", "\u6d77\u5357\u6821\u533a"]):
        return "\u6d77\u5357"
    m = re.search(r"([^\s\uff0c,\u3002\uff1b;]{1,12}\u6821\u533a)", src)
    if m:
        return m.group(1)
    return ""


def _detect_lab_keyword(text: str) -> str:
    src = str(text or "").strip()
    if not src:
        return ""
    m = re.search(r"([^\s\uff0c,\u3002\uff1b;]{1,24}?\u5b9e\u9a8c\u5ba4)", src)
    if not m:
        return ""
    token = m.group(1).strip()
    token = re.sub(
        r"^(?:\u67e5\u8be2|\u67e5\u770b|\u67e5|\u770b\u770b|\u770b\u4e00\u4e0b|\u770b\u4e0b|\u770b|\u5e2e\u6211\u67e5|\u5e2e\u5fd9\u67e5|\u8bf7\u67e5)+",
        "",
        token,
    ).strip()
    if token in {"\u5b9e\u9a8c\u5ba4", "\u65e5\u62a5\u5b9e\u9a8c\u5ba4"}:
        return ""
    return token[:24]


def _safe_iso_date(year: int, month: int, day: int) -> str:
    try:
        return date(year, month, day).isoformat()
    except Exception:
        return ""


def _normalize_date(value: Any) -> str:
    token = str(value or "").strip()
    if not token:
        return ""
    m = re.fullmatch(r"(20\d{2})-(\d{1,2})-(\d{1,2})", token)
    if m:
        return _safe_iso_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m2 = re.fullmatch(r"(20\d{2})[/.年](\d{1,2})[-/.月](\d{1,2})日?", token)
    if m2:
        return _safe_iso_date(int(m2.group(1)), int(m2.group(2)), int(m2.group(3)))
    m3 = re.fullmatch(r"(\d{1,2})\u6708(\d{1,2})\u65e5", token)
    if m3:
        return _safe_iso_date(date.today().year, int(m3.group(1)), int(m3.group(2)))
    m4 = re.fullmatch(r"(\d{1,2})[-/.](\d{1,2})", token)
    if m4:
        return _safe_iso_date(date.today().year, int(m4.group(1)), int(m4.group(2)))
    return ""


def _normalize_request_status(value: Any) -> str:
    token = str(value or "").strip().lower()
    return token if token in {"pending", "approved", "rejected"} else ""


def _normalize_asset_status(value: Any) -> str:
    token = str(value or "").strip().lower()
    return token if token in {"in_use", "spare", "repair"} else ""


def _normalize_limit(value: Any) -> int:
    parsed = _safe_int(value)
    if not parsed or parsed <= 0:
        return DEFAULT_LIMIT
    return min(parsed, MAX_LIMIT)


def _safe_int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except Exception:
        return None


def _extract_after_keyword(text: str, keywords: List[str]) -> str:
    for keyword in keywords:
        m = re.search(rf"{re.escape(keyword)}[:：]?\s*([^\s\uff0c,\u3002\uff1b;]+)", text or "")
        if m:
            return m.group(1).strip()
    return ""


def _extract_quoted_keyword(text: str) -> str:
    m = re.search(r"[\"“](.+?)[\"”]", text or "")
    return m.group(1).strip()[:60] if m else ""


def _extract_keyword_from_sentence(text: str, lowered: str) -> str:
    if not _contains_any(text, ["\u641c\u7d22", "\u67e5\u627e", "\u5305\u542b", "\u5173\u952e\u5b57", "\u5173\u952e\u8bcd", "\u540d\u5b57", "\u540d\u79f0"]):
        return ""

    m_contains = re.search(
        r'(?:\u5305\u542b|\u542b\u6709|\u542b)\s*["\'\u201c\u201d]?([^"\'\u201c\u201d\uff0c,\u3002\uff1b;]+)',
        text or "",
    )
    if m_contains:
        candidate = m_contains.group(1).strip()
        candidate = re.sub(r"(\u7684)?(\u65e5\u62a5|\u8bb0\u5f55|\u5185\u5bb9)$", "", candidate).strip()
        if candidate:
            return candidate[:40]

    cleaned = re.sub(r"[\uff0c\u3002\uff1b;,.!?]", " ", text or "").strip()
    for noisy in [
        "\u641c\u7d22",
        "\u67e5\u627e",
        "\u5305\u542b",
        "\u542b\u6709",
        "\u5173\u952e\u5b57",
        "\u5173\u952e\u8bcd",
        "\u5185\u5bb9\u91cc",
        "\u5185\u5bb9\u4e2d",
        "\u5185\u5bb9",
        "\u540d\u5b57",
        "\u540d\u79f0",
        "\u7684",
        "\u8bb0\u5f55",
        "\u6570\u636e",
        "\u8d44\u4ea7",
        "\u65e5\u62a5",
    ]:
        cleaned = cleaned.replace(noisy, " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned or len(cleaned) > 40:
        return ""
    if cleaned.lower() == lowered:
        return ""
    return cleaned

def _sanitize_daily_merged_filters(filters: Dict[str, Any], message: str) -> Dict[str, Any]:
    sanitized = dict(filters or {})
    keyword = str(sanitized.get("keyword") or "").strip()
    if keyword:
        if not _contains_any(message, ["\u641c\u7d22", "\u67e5\u627e", "\u5305\u542b", "\u5173\u952e\u8bcd", "\u5173\u952e\u5b57", "\u540d\u5b57", "\u540d\u79f0"]):
            sanitized.pop("keyword", None)
        elif keyword in {
            "\u4eca\u5929",
            "\u6628\u5929",
            "\u524d\u5929",
            "\u672c\u5468",
            "\u8fd9\u5468",
            "\u672c\u661f\u671f",
            "\u8fd9\u661f\u671f",
            "\u4e0a\u5468",
            "\u6700\u8fd1\u4e09\u5929",
            "\u8fd1\u4e09\u5929",
            "\u5f85\u5ba1\u6838",
            "\u5df2\u901a\u8fc7",
            "\u5df2\u9a73\u56de",
            "\u9a73\u56de",
            "\u901a\u8fc7",
            "\u65e5\u62a5",
            "\u8bb0\u5f55",
        }:
            sanitized.pop("keyword", None)
        elif len(keyword) <= 1:
            sanitized.pop("keyword", None)
    return sanitized

def _contains_any(text: str, tokens: List[str]) -> bool:
    src = str(text or "")
    return any(token in src for token in tokens)


def _resolve_daily_date_range(filters: Dict[str, Any]) -> Tuple[Optional[date], Optional[date]]:
    report_date = _normalize_date(filters.get("report_date"))
    if report_date:
        try:
            d = date.fromisoformat(report_date)
            return d, d
        except Exception:
            return None, None

    scope = str(filters.get("time_scope") or "").strip().lower()
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    if scope == "this_week":
        return week_start, week_end
    if scope == "last_week":
        last_start = week_start - timedelta(days=7)
        return last_start, last_start + timedelta(days=6)
    if scope == "recent_3_days":
        return today - timedelta(days=2), today
    return None, None


def _is_row_in_date_range(row: Dict[str, Any], start_date: date, end_date: date) -> bool:
    token = str(row.get("report_date") or "").strip()
    if not token:
        return False
    try:
        d = date.fromisoformat(token)
    except Exception:
        return False
    return start_date <= d <= end_date


def _filter_daily_rows(rows: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    keyword = str(filters.get("keyword") or "").strip().lower()
    lab_name = str(filters.get("lab_name") or "").strip().lower()
    lab_core = _normalize_lab_core_keyword(lab_name)
    reporter_name = str(filters.get("reporter_name") or "").strip().lower()
    campus_name = str(filters.get("campus_name") or "").strip().lower()
    if not keyword and not lab_name and not reporter_name and not campus_name:
        return rows

    def _hit(row: Dict[str, Any]) -> bool:
        lab_text = str(row.get("lab_name") or "").lower()
        reporter_text = str(row.get("reporter_name") or "").lower()
        campus_text = str(row.get("campus_name") or "").lower()
        if lab_name and (lab_name not in lab_text and (not lab_core or lab_core not in lab_text)):
            return False
        if reporter_name and reporter_name not in reporter_text:
            return False
        if campus_name and campus_name not in campus_text:
            return False
        if not keyword:
            return True
        merged = (
            f"{row.get('lab_name') or ''} "
            f"{row.get('reporter_name') or ''} "
            f"{row.get('content') or ''} "
            f"{row.get('campus_name') or ''}"
        ).lower()
        return keyword in merged

    return [row for row in rows if _hit(row)]


def _normalize_lab_core_keyword(lab_name: str) -> str:
    token = str(lab_name or "").strip().lower()
    if not token:
        return ""
    if token.endswith("\u5b9e\u9a8c\u5ba4"):
        token = token[: -len("\u5b9e\u9a8c\u5ba4")]
    token = token.strip()
    if len(token) <= 1:
        return ""
    return token


def _filter_request_rows(rows: List[Dict[str, Any]], filters: Dict[str, Any], category: str) -> List[Dict[str, Any]]:
    keyword = str(filters.get("keyword") or "").strip().lower()
    category_kw = category.lower()

    def _hit(row: Dict[str, Any]) -> bool:
        if category_kw and category_kw not in str(row.get("category") or "").lower():
            return False
        if not keyword:
            return True
        merged = (
            f"{row.get('request_no') or ''} "
            f"{row.get('asset_name') or ''} "
            f"{row.get('requester_name') or ''} "
            f"{row.get('campus_name') or ''} "
            f"{row.get('category') or ''}"
        ).lower()
        return keyword in merged

    return [row for row in rows if _hit(row)]


def _filter_asset_rows(rows: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    keyword = str(filters.get("keyword") or "").strip().lower()
    if not keyword:
        return rows

    def _hit(row: Dict[str, Any]) -> bool:
        merged = (
            f"{row.get('asset_code') or ''} "
            f"{row.get('asset_name') or ''} "
            f"{row.get('category') or ''} "
            f"{row.get('campus_name') or ''} "
            f"{row.get('lab_name') or ''} "
            f"{_extract_asset_meta_text(row)}"
        ).lower()
        return keyword in merged

    return [row for row in rows if _hit(row)]


def _extract_asset_meta_text(row: Dict[str, Any]) -> str:
    description = str(row.get("description") or "")
    if META_FLAG not in description:
        return description
    idx = description.rfind(META_FLAG)
    prefix = description[:idx]
    meta_text = description[idx + len(META_FLAG):].strip()
    try:
        payload = json.loads(meta_text)
        if isinstance(payload, dict):
            return f"{prefix} {' '.join(str(v or '') for v in payload.values())}"
    except Exception:
        pass
    return description


def _build_reply(reply: Any, total: int, target_name: str) -> str:
    text = str(reply or "").strip()
    if text:
        return f"{text} 共匹配 {total} 条{target_name}记录。"
    return f"已完成自然语言查询，共匹配 {total} 条{target_name}记录。"


def _llm_enabled() -> bool:
    provider = str(getattr(Config, "AGENT_PROVIDER", "") or "").strip().lower()
    return provider in {"openai", "deepseek", "llm"} and bool(getattr(Config, "LLM_API_KEY", ""))


def _compact_filters(filters: Dict[str, Any]) -> Dict[str, Any]:
    compacted: Dict[str, Any] = {}
    for key, value in (filters or {}).items():
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        compacted[key] = value
    return compacted


def _is_blank_filter_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return False

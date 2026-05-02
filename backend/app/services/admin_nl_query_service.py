import json
import re
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

import requests

from app.config import Config
from app.services.asset_service import list_asset_requests, list_assets
from app.services.lab_report_service import list_daily_reports
from app.utils.exceptions import AppError

DEFAULT_LIMIT = 200
MAX_LIMIT = 500
META_FLAG = "__META__="


def query_admin_data(current_user, domain: str, message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    normalized_domain = str(domain or "").strip().lower()
    if normalized_domain not in {"daily_reports", "assets"}:
        raise AppError("domain 仅支持 daily_reports 或 assets", 400, 40098)

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
    campus_id = _safe_int(filters.get("campus_id"))
    limit = _normalize_limit(filters.get("limit"))

    if status:
        service_filters["status"] = status
    if report_date:
        service_filters["report_date"] = report_date
    if campus_id and campus_id > 0:
        service_filters["campus_id"] = campus_id

    rows = list_daily_reports(current_user, service_filters)
    rows = _filter_daily_rows(rows, filters)
    total = len(rows)
    rows = rows[:limit]

    return {
        "reply": _build_reply(plan.get("reply"), total, "巡查结果"),
        "filters": {
            "status": status or "",
            "report_date": report_date or "",
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
    service_filters = {}
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
        merged_filters.update(planned_filters)
        return {
            "mode": planned.get("mode") or fallback.get("mode", ""),
            "filters": merged_filters,
            "reply": str(planned.get("reply") or "").strip(),
        }
    except Exception:
        return fallback


def _plan_with_llm(domain: str, message: str, context: Dict[str, Any]) -> Dict[str, Any]:
    system_prompt = (
        "你是管理后台查询解析器。只输出 JSON，不要输出解释。\n"
        "JSON 结构: {\"mode\":\"\", \"filters\":{}, \"reply\":\"\"}\n"
        "domain=daily_reports 时 mode 为空字符串；filters 可用键: status, report_date, campus_id, lab_name, reporter_name, keyword, limit。\n"
        "domain=assets 时 mode 只能是 requests 或 assets；\n"
        "requests 模式 filters 可用键: status, category, campus_id, keyword, limit；\n"
        "assets 模式 filters 可用键: asset_status, category, campus_id, keyword, limit。\n"
        "status 仅允许 pending/approved/rejected；asset_status 仅允许 in_use/spare/repair。\n"
        "report_date 必须是 YYYY-MM-DD。"
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
        if _contains_any(text, ["入库", "台账", "资产编码", "厂家", "规格"]):
            mode = "assets"
        elif _contains_any(text, ["申报", "审批", "申请单", "申请记录"]):
            mode = "requests"
        else:
            mode = str(context.get("mode") or "requests").strip().lower()
            if mode not in {"requests", "assets"}:
                mode = "requests"

    if domain == "daily_reports":
        status = _normalize_request_status(_detect_status_token(text))
        report_date = _detect_date(text)
        if status:
            filters["status"] = status
        if report_date:
            filters["report_date"] = report_date
    elif mode == "requests":
        status = _normalize_request_status(_detect_status_token(text))
        if status:
            filters["status"] = status
        category = _extract_after_keyword(text, ["分类", "类别"])
        if category:
            filters["category"] = category
    else:
        status = _normalize_asset_status(_detect_asset_status_token(text))
        if status:
            filters["asset_status"] = status
        category = _extract_after_keyword(text, ["分类", "类别"])
        if category:
            filters["category"] = category

    keyword = _extract_quoted_keyword(text) or _extract_keyword_from_sentence(text, lowered)
    if keyword:
        filters["keyword"] = keyword

    return {"mode": mode, "filters": filters, "reply": ""}


def _detect_status_token(text: str) -> str:
    if _contains_any(text, ["待审核", "待审批", "pending"]):
        return "pending"
    if _contains_any(text, ["已通过", "通过", "approved"]):
        return "approved"
    if _contains_any(text, ["已驳回", "驳回", "rejected"]):
        return "rejected"
    return ""


def _detect_asset_status_token(text: str) -> str:
    if _contains_any(text, ["在用", "使用中", "in_use"]):
        return "in_use"
    if _contains_any(text, ["备用", "spare"]):
        return "spare"
    if _contains_any(text, ["维修", "维修中", "repair"]):
        return "repair"
    return ""


def _detect_date(text: str) -> str:
    today = date.today()
    m_cn = re.search(r"(\d{1,2})\u6708(\d{1,2})\u65e5", text or "")
    if m_cn:
        return _safe_iso_date(today.year, int(m_cn.group(1)), int(m_cn.group(2)))

    m_ymd = re.search(r"(20\d{2})[-/.年](\d{1,2})[-/.月](\d{1,2})", text or "")
    if m_ymd:
        return _safe_iso_date(int(m_ymd.group(1)), int(m_ymd.group(2)), int(m_ymd.group(3)))

    m_md = re.search(r"(?<!\d)(\d{1,2})[-/.](\d{1,2})(?!\d)", text or "")
    if m_md:
        return _safe_iso_date(today.year, int(m_md.group(1)), int(m_md.group(2)))

    if "今天" in (text or ""):
        return today.isoformat()
    if "昨天" in (text or ""):
        return (today - timedelta(days=1)).isoformat()
    if "前天" in (text or ""):
        return (today - timedelta(days=2)).isoformat()
    return ""


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
    if token in {"pending", "approved", "rejected"}:
        return token
    return ""


def _normalize_asset_status(value: Any) -> str:
    token = str(value or "").strip().lower()
    if token in {"in_use", "spare", "repair"}:
        return token
    return ""


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
        m = re.search(rf"{re.escape(keyword)}[:：]?\s*([^\s，,。；;]+)", text)
        if m:
            return m.group(1).strip()
    return ""


def _extract_quoted_keyword(text: str) -> str:
    m = re.search(r"[\"“](.+?)[\"”]", text)
    return m.group(1).strip()[:60] if m else ""


def _extract_keyword_from_sentence(text: str, lowered: str) -> str:
    if not _contains_any(text, ["搜索", "查找", "包含", "关键字", "关键词", "名字", "名称"]):
        return ""
    cleaned = re.sub(r"[，。；;,.!?！？]", " ", text).strip()
    for noisy in ["搜索", "查找", "包含", "关键字", "关键词", "名字", "名称", "的", "记录", "数据", "资产", "日报"]:
        cleaned = cleaned.replace(noisy, " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned or len(cleaned) > 40:
        return ""
    if cleaned.lower() == lowered:
        return ""
    return cleaned


def _contains_any(text: str, tokens: List[str]) -> bool:
    src = str(text or "")
    return any(token in src for token in tokens)


def _filter_daily_rows(rows: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    keyword = str(filters.get("keyword") or "").strip().lower()
    lab_name = str(filters.get("lab_name") or "").strip().lower()
    reporter_name = str(filters.get("reporter_name") or "").strip().lower()
    if not keyword and not lab_name and not reporter_name:
        return rows

    def _hit(row: Dict[str, Any]) -> bool:
        lab_text = str(row.get("lab_name") or "").lower()
        reporter_text = str(row.get("reporter_name") or "").lower()
        if lab_name and lab_name not in lab_text:
            return False
        if reporter_name and reporter_name not in reporter_text:
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

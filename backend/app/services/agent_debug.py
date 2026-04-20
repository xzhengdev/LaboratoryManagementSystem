from datetime import datetime
from typing import Any, Dict, List, Tuple
from zoneinfo import ZoneInfo

from app.config import Config


DEFAULT_AGENT_TIMEZONE = "Asia/Shanghai"

_DEBUG_EVENT_META: Dict[str, Tuple[str, str]] = {
    "chat_received": ("chat", "收到用户输入"),
    "chat_rejected": ("chat", "用户校验失败"),
    "route": ("chat", "路由分支"),
    "agent_loop_start": ("_agent_loop", "开始智能循环"),
    "fallback_rule": ("_agent_loop", "降级到规则引擎"),
    "form_initialized": ("_agent_loop", "初始化表单"),
    "llm_decision": ("_llm_agent_decide", "LLM 决策"),
    "auto_fill_params": ("_auto_fill_params", "自动补参"),
    "params_filled": ("_agent_loop", "补参完成"),
    "run_tool_enter": ("_run_tool", "执行工具"),
    "run_tool_missing_fields": ("_run_tool", "缺少必填参数"),
    "run_tool_unknown": ("_run_tool", "未知工具"),
    "tool_executed": ("_run_tool", "工具执行结果"),
    "form_synced_by_tool": ("_agent_loop", "根据工具结果回填表单"),
    "pending_action_set": ("_agent_loop", "挂起待续动作"),
    "pending_action_continue": ("chat", "续接待续动作"),
    "pending_action_cleared": ("chat", "清除待续动作"),
    "done_return": ("_agent_loop", "任务完成返回"),
    "agent_loop_exception_fallback": ("chat", "Agent异常，进入兜底"),
    "fallback_exception_general_llm": ("chat", "兜底异常，转通用LLM"),
}


def _localized_now() -> datetime:
    tz_name = str(getattr(Config, "AGENT_TIMEZONE", DEFAULT_AGENT_TIMEZONE) or DEFAULT_AGENT_TIMEZONE)
    try:
        return datetime.now(ZoneInfo(tz_name))
    except Exception:
        return datetime.now()


def _debug_enabled() -> bool:
    raw = str(getattr(Config, "AGENT_DEBUG_TRACE", "") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _debug_clip(value: Any, limit: int = 60) -> str:
    text = str(value)
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def _debug_brief_payload(event: str, payload: Dict[str, Any]) -> str:
    if not payload:
        return ""
    preferred_keys: Dict[str, List[str]] = {
        "chat_received": ["message"],
        "route": ["target", "lab_related", "lab_followup"],
        "llm_decision": ["step", "tool", "done", "params"],
        "auto_fill_params": ["tool", "out_params"],
        "params_filled": ["step", "tool", "params"],
        "run_tool_enter": ["tool", "params"],
        "run_tool_missing_fields": ["tool", "missing"],
        "tool_executed": ["step", "tool", "ok", "error_code", "data_preview"],
        "form_synced_by_tool": ["step", "tool", "form"],
        "pending_action_set": ["tool", "missing"],
        "pending_action_continue": ["tool", "message"],
        "pending_action_cleared": ["tool"],
        "done_return": ["step", "reply_preview"],
    }
    keys = preferred_keys.get(event) or list(payload.keys())[:3]
    parts: List[str] = []
    for key in keys:
        if key not in payload:
            continue
        value = payload.get(key)
        if isinstance(value, dict):
            compact = {}
            for sub in ["date", "start_time", "end_time", "lab_id", "participant_count", "preference", "purpose"]:
                if sub in value and value.get(sub) not in [None, ""]:
                    compact[sub] = value.get(sub)
            value = compact or value
        parts.append(f"{key}={_debug_clip(value)}")
    return " | ".join(parts)


def debug_log(trace_id: str, event: str, **payload: Any) -> None:
    if not _debug_enabled():
        return
    now = _localized_now().strftime("%Y-%m-%d %H:%M:%S")
    func_name, desc = _DEBUG_EVENT_META.get(event, ("-", event))
    body = _debug_brief_payload(event, payload)
    if body:
        print(f"[AGENT][{now}][{trace_id}] {func_name} | {desc} | {body}")
    else:
        print(f"[AGENT][{now}][{trace_id}] {func_name} | {desc}")


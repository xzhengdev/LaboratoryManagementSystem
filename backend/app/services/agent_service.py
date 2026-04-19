import json
import re
from datetime import date, datetime, time, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4
from zoneinfo import ZoneInfo

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
DEFAULT_AGENT_TIMEZONE = "Asia/Shanghai"
WEEKDAY_CN = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]

#xinzhu修改
AGENT_TOOL_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "query_labs": {
        "required": [],
        "optional": ["date", "campus", "type", "participant_count"],
        "description": "查询实验室列表，支持按日期、校区、实验室类型、参与人数等条件筛选可用实验室。",
        "returns": "返回实验室列表，每项通常包含实验室ID、名称、容量、校区、开放时间、状态等基础信息。"
    },

    "query_schedule": {
        "required": ["date"],
        "optional": ["lab_id"],
        "description": "查询某一天的实验室排期信息，可查询单个实验室或多个实验室的预约占用情况。",
        "returns": "返回指定日期的排期结果，包括实验室开放时间、已预约时间段、预约状态等信息。"
    },

    "check_availability": {
        "required": ["lab_id", "date", "start_time", "end_time"],
        "optional": [],
        "description": "检查指定实验室在某一天某个时间段是否可预约，用于避免时间冲突和非法预约。",
        "returns": "返回该时间段是否可预约的判断结果，通常包含是否可用、冲突原因或冲突时间段等信息。"
    },

    "recommend_time": {
        "required": ["date"],
        "optional": ["lab_id", "preference"],
        "description": "根据实验室排期和用户偏好，为用户推荐某一天最合适的预约时间段。",
        "returns": "返回推荐时间结果，通常包含推荐的开始时间、结束时间、实验室ID、实验室名称及推荐理由。"
    },

    "recommend_lab": {
        "required": ["date"],
        "optional": ["participant_count", "type", "campus"],
        "description": "根据日期、人数、实验室类型、校区等条件，为用户推荐最合适的实验室。",
        "returns": "返回推荐实验室结果，通常包含实验室ID、名称、容量、校区及推荐理由。"
    },

    "get_lab_detail": {
        "required": ["lab_id"],
        "optional": [],
        "description": "获取指定实验室的详细信息，包括实验室描述、容量、设备、位置等。",
        "returns": "返回实验室详情，通常包含实验室名称、位置、容量、设备列表、开放时间、状态、描述等信息。"
    },

    "create_reservation": {
        "required": ["lab_id", "date", "start_time", "end_time", "participant_count", "purpose"],
        "optional": [],
        "description": "创建新的实验室预约记录，是实验室预约流程中的最终执行动作。",
        "returns": "返回预约创建结果，通常包含预约ID、实验室名称、预约日期、开始时间、结束时间、预约状态等信息。"
    },

    "update_reservation": {
        "required": ["reservation_id"],
        "optional": ["date", "start_time", "end_time"],
        "description": "修改已有预约记录，可调整预约日期或时间段。",
        "returns": "返回预约修改结果，通常包含修改后的预约信息、更新时间以及当前状态。"
    },

    "cancel_reservation": {
        "required": ["reservation_id"],
        "optional": [],
        "description": "取消指定的实验室预约记录，用于预约生命周期管理中的撤销操作。",
        "returns": "返回预约取消结果，通常包含预约ID、取消状态、处理结果说明等信息。"
    },

    "my_reservations": {
        "required": [],
        "optional": [],
        "description": "查询当前用户的预约记录列表，用于查看个人预约历史和当前预约状态。",
        "returns": "返回当前用户的预约列表，每项通常包含预约ID、实验室名称、日期、时间段、状态等信息。"
    },

    "explain_rules": {
        "required": [],
        "optional": ["question"],
        "description": "解释实验室预约相关规则、限制和原因，用于回答用户关于预约制度的疑问。",
        "returns": "返回规则解释文本，通常包括预约限制、开放时间要求、人数限制、审批规则或违规原因说明。"
    },

    "navigate": {
        "required": ["path"],
        "optional": [],
        "description": "驱动前端页面跳转，将用户带到指定的小程序页面。",
        "returns": "返回页面跳转动作信息，通常包含目标页面路径及跳转说明。"
    },

    "fill_form": {
        "required": ["form"],
        "optional": [],
        "description": "自动填写前端页面中的预约表单数据，用于实现AI辅助填表。",
        "returns": "返回表单填充动作信息，通常包含目标表单标识和需要填入的字段内容。"
    },

    "submit_form": {
        "required": [],
        "optional": [],
        "description": "自动提交当前已填写完成的表单，用于完成预约流程中的最终前端提交动作。",
        "returns": "返回表单提交动作结果，通常包含提交是否成功、反馈信息或后续提示。"
    },
}

AGENT_SESSIONS: Dict[int, Dict[str, Any]] = {}


def _localized_now() -> datetime:
    tz_name = str(getattr(Config, "AGENT_TIMEZONE", DEFAULT_AGENT_TIMEZONE) or DEFAULT_AGENT_TIMEZONE)
    try:
        return datetime.now(ZoneInfo(tz_name))
    except Exception:
        return datetime.now()


def _now() -> datetime:
    return datetime.now()


def _today() -> date:
    return _localized_now().date()


def _new_trace_id() -> str:
    return f"agt-{uuid4().hex[:12]}"


def _debug_enabled() -> bool:
    raw = str(getattr(Config, "AGENT_DEBUG_TRACE", "") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _debug_log(trace_id: str, event: str, **payload: Any) -> None:
    if not _debug_enabled():
        return
    now = _localized_now().strftime("%Y-%m-%d %H:%M:%S")
    body = ""
    if payload:
        try:
            body = " " + json.dumps(payload, ensure_ascii=False, default=str)
        except Exception:
            body = f" {str(payload)}"
    print(f"[AGENT][{now}][{trace_id}][{event}]{body}")


def _tool_call(tool: str, params: Dict[str, Any], reply: str) -> Dict[str, Any]:
    return {"type": "tool_call", "tool": tool, "params": params, "reply": reply}


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
    out: Dict[str, Any] = {
        "ok": ok,
        "tool": tool,
        "data": data,
        "error_code": error_code,
        "error_message": error_message,
    }
    if raw is not None:
        out["raw"] = raw
    if extra:
        out.update(extra)
    return out


def _normalize_params_shape(params: Any) -> Dict[str, Any]:
    return dict(params) if isinstance(params, dict) else {}


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
        labels = [label_map.get(x, x) for x in missing]
        return "还缺少这些信息: " + "、".join(labels) + "。"
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
    """
    调用 LLM API 的核心函数 - 与大语言模型通信的统一接口
    这是整个系统中与 LLM 通信的唯一入口，负责：
    1. 验证 API 配置是否完整
    2. 构建符合 OpenAI API 格式的请求
    3. 发送 HTTP 请求并处理响应
    4. 提取并返回模型生成的文本内容
    
    支持的 API 格式：
    - OpenAI API 格式（兼容 DeepSeek、通义千问等）
    - 标准 Chat Completion 接口
    
    Args:
        messages: 消息列表，每个消息包含 role 和 content
            格式: [
                {"role": "system", "content": "系统提示词"},
                {"role": "user", "content": "用户消息"},
                {"role": "assistant", "content": "助手回复"}
            ]
            role 可选值: system, user, assistant
        temperature: 温度参数，控制输出的随机性
            - 0: 确定性输出（相同输入得到相同输出）
            - 0.5: 中等随机性
            - 1.0: 高随机性（创意性更强）
            默认 0.1，平衡稳定性和多样性
    """
    # ==================== 1. 配置验证 ====================
    # 检查 API Key 是否已配置如果没有配置，提前抛出异常，避免无意义的网络请求
    if not Config.LLM_API_KEY:
        raise RuntimeError("missing LLM_API_KEY")
    # ==================== 2. 构建请求头 ====================
    # Authorization: Bearer Token 认证（OpenAI 标准格式）
    # Content-Type: 告诉服务端请求体是 JSON 格式
    headers = {
        "Authorization": f"Bearer {Config.LLM_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # ==================== 3. 构建请求体 ====================
    # model: 使用的模型名称（从配置读取）
    # messages: 对话消息列表
    # temperature: 控制随机性
    payload = {
        "model": Config.AGENT_MODEL,
        "messages": messages,
        "temperature": temperature
    }
    
    # ==================== 4. 发送 HTTP 请求 ====================
    # timeout=35: 35秒超时限制，防止长时间阻塞
    # 如果超时，requests 会抛出 Timeout 异常
    resp = requests.post(
        Config.LLM_BASE_URL,  # API 端点地址
        headers=headers,
        json=payload,         # 自动将 dict 序列化为 JSON
        timeout=35
    )
    
    # ==================== 5. 检查响应状态 ====================
    # raise_for_status() 会在 HTTP 状态码不是 2xx 时抛出异常
    # 例如：401 Unauthorized, 429 Too Many Requests, 500 Internal Error
    resp.raise_for_status()
    
    # ==================== 6. 解析响应并提取内容 ====================
    # 将 JSON 字符串解析为 Python 字典
    data = resp.json()
   
    # 提取第一 choice 的 message.content
    # 响应格式遵循 OpenAI Chat Completion API
    # data["choices"][0]["message"]["content"] 是标准路径
    content = str(data["choices"][0]["message"]["content"]).strip()
    # print(content)
    return content


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
    """
    清理或初始化用户会话
    1. 检查会话是否过期（超过 SESSION_TTL_MINUTES 分钟无操作）
    2. 过期则重置会话（清空所有数据）
    3. 初始化会话的默认结构（预约表单、查询历史等）
    4. 更新时间戳
    会话过期机制可以防止内存无限增长，同时保留活跃用户的对话状态。
    Args:
        user_id: 用户ID，作为会话的唯一标识
    Returns:
        Dict[str, Any]: 用户会话对象，包含以下字段：
            - reservation_form (dict): 预约表单，存储用户正在填写的预约信息
            - last_labs (list): 最近查询的实验室列表（用于序号选择）
            - last_reservations (list): 最近查询的预约列表（用于序号选择）
            - updated_at (datetime): 最后更新时间戳
    Example:
        >>> session = _clean_session(12345)
        >>> session["reservation_form"]["date"] = "2026-04-20"
        >>> # 会话会自动管理过期，无需手动清理
    """
    # 获取当前时间（用于过期判断和时间戳更新）
    now = _now()
    # ==================== 1. 获取现有会话 ====================
    # 从全局会话字典中获取该用户的会话数据
    # 如果不存在则初始化为空字典
    session = AGENT_SESSIONS.get(user_id) or {}
    # ==================== 2. 会话过期检查 ====================
    # 获取会话的最后更新时间
    last = session.get("updated_at")
    # 判断会话是否过期：
    # - 没有更新时间记录（新会话或异常）
    # - 或当前时间减去最后更新时间超过 TTL（Time To Live）
    if not last or (now - last).total_seconds() > SESSION_TTL_MINUTES * 60:
        # 会话已过期，重置为空字典（丢弃所有历史数据）
        session = {}
    # ==================== 3. 初始化会话默认结构 ====================
    # setdefault 确保字段存在，如果不存在则设置默认值
    # 这样既保留了已有数据，又能保证结构完整
    # 3.1 预约表单：存储用户正在填写的预约信息
    # 支持多轮对话逐步收集预约信息
    session.setdefault(
        "reservation_form",
        {
            "date": "",                    # 预约日期 (YYYY-MM-DD)
            "start_time": "",              # 开始时间 (HH:MM)
            "end_time": "",                # 结束时间 (HH:MM)
            "participant_count": None,     # 参与人数
            "purpose": "",                 # 用途说明
            "lab_id": None,                # 实验室ID
            "campus": "",                  # 校区（用于实验室筛选）
            "type": "",                    # 实验室类型（用于筛选）
        },
    )
    # 3.2 最近查询的实验室列表
    # 用于支持用户通过序号选择实验室（例如："选第1个"）
    session.setdefault("last_labs", [])
    # 3.3 最近查询的预约列表
    # 用于支持用户通过序号取消预约（例如："取消第2个"）
    session.setdefault("last_reservations", [])
    # 3.4 最后更新时间戳
    # 用于会话过期判断，每次操作都会更新
    session.setdefault("updated_at", now)
    # ==================== 4. 保存并返回 ====================
    # 将会话写回全局字典
    AGENT_SESSIONS[user_id] = session
    # 返回会话对象供调用方使用
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


def _relative_day_offset(text: str) -> Optional[int]:
    msg = text or ""
    if "后天" in msg:
        return 2
    if "明天" in msg:
        return 1
    if "今天" in msg:
        return 0
    return None


def _resolve_relative_date(text: str) -> Optional[str]:
    offset = _relative_day_offset(text)
    if offset is None:
        return None
    return (_today() + timedelta(days=offset)).isoformat()


def _detect_date(text: str) -> Optional[str]:
    msg = text or ""
    today = _today()
    relative = _resolve_relative_date(msg)
    if relative:
        return relative
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


def _detect_preference(text: str) -> str:
    msg = text or ""
    if "下午" in msg or "晚上" in msg:
        return "下午"
    if "上午" in msg or "早上" in msg:
        return "上午"
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
    prompt = (
        "从用户输入中抽取预约字段并仅返回 JSON。"
        f"已有表单: {json.dumps(form, ensure_ascii=False)}。"
        f"用户输入: {text}"
    )
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


def _is_date_time_question(text: str) -> bool:
    msg = (text or "").strip().lower()
    keys = [
        "今天几号",
        "今天是几号",
        "今天几月几号",
        "今天日期",
        "明天几号",
        "明天是几号",
        "后天几号",
        "昨天几号",
        "几号",
        "几月几日",
        "星期几",
        "周几",
        "礼拜几",
        "现在几点",
        "现在时间",
        "time",
        "date",
    ]
    return any(k in msg for k in keys)


def _resolve_date_target(text: str, today: date) -> date:
    msg = (text or "").strip()

    # Relative date first.
    if "大后天" in msg:
        return today + timedelta(days=3)
    if "后天" in msg:
        return today + timedelta(days=2)
    if "明天" in msg:
        return today + timedelta(days=1)
    if "前天" in msg:
        return today - timedelta(days=2)
    if "昨天" in msg:
        return today - timedelta(days=1)
    if "今天" in msg:
        return today

    # ISO date: 2026-04-20
    m = re.search(r"(20\d{2})-(\d{1,2})-(\d{1,2})", msg)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except Exception:
            pass

    # Chinese month/day: 4?20?
    m2 = re.search("(\d{1,2})月(\d{1,2})日", msg)
    if m2:
        try:
            return date(today.year, int(m2.group(1)), int(m2.group(2)))
        except Exception:
            pass

    # Weekday expressions: ??? / ??? / ?? / ???
    weekday_map = {
        "一": 0,
        "二": 1,
        "三": 2,
        "四": 3,
        "五": 4,
        "六": 5,
        "日": 6,
        "天": 6,
    }
    m3 = re.search("(本周|这周|下周)?(?:星期|周|礼拜)([一二三四五六日天])", msg)
    if m3:
        prefix = m3.group(1) or ""
        target_wd = weekday_map.get(m3.group(2), today.weekday())
        cur_wd = today.weekday()
        delta = (target_wd - cur_wd) % 7
        if prefix == "下周":
            delta += 7
        return today + timedelta(days=delta)

    return today


def _build_date_time_reply(text: str = "") -> str:
    now = _localized_now()
    today = now.date()
    target = _resolve_date_target(text, today)
    weekday = WEEKDAY_CN[target.weekday()]

    msg = (text or "").strip()
    ask_time = any(k in msg for k in ["几点", "时间", "time"])

    if target == today and ask_time:
        return f"今天是 {today.strftime('%Y-%m-%d')}（{weekday}），当前时间 {now.strftime('%H:%M:%S')}。"

    if target == today:
        label = "今天"
    elif target == today + timedelta(days=1):
        label = "明天"
    elif target == today + timedelta(days=2):
        label = "后天"
    elif target == today - timedelta(days=1):
        label = "昨天"
    else:
        label = "你问的日期"

    return f"{label}是 {target.strftime('%Y-%m-%d')}（{weekday}）。"

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
        filtered: List[Laboratory] = []
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
    best = None
    best_score = -1
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
            # Honor explicit user preference first.
            if "上午" in preference and s >= 12 * 60:
                continue
            if "下午" in preference and s < 12 * 60:
                continue
            score = dur
            if "上午" in preference and s < 12 * 60:
                score += 30
            if "下午" in preference and s >= 12 * 60:
                score += 30
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
    relative_date = _resolve_relative_date(text)
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
    # 相对日期强制优先，避免被 LLM 错误覆盖
    if relative_date:
        merged["date"] = relative_date
    if not merged.get("participant_count"):
        merged["participant_count"] = 1
    return merged


def _normalize_chat_result(result: Any, trace_id: str = "") -> Dict[str, Any]:
    """
    标准化聊天结果为统一格式
    这是响应格式的统一出口，确保所有返回给前端的数据结构一致。
    主要功能：
    1. 将各种输入格式（字符串、字典、工具调用等）统一为 {reply, actions, trace_id}
    2. 为特定工具调用添加快捷操作按钮（actions）
    3. 确保 trace_id 存在（用于日志追踪）
    为什么要标准化？
    - 前端只需要处理一种数据格式
    - 便于添加统一的日志、监控逻辑
    - 避免因返回格式不一致导致的 UI 错误
    
    Args:
        result: 原始结果，可以是以下类型：
            - str: 纯文本回复
            - dict: 可能包含 reply, actions, type, tool, params 等字段
            - None: 空结果
        trace_id: 可选的追踪ID，如果 result 中没有则会使用此值或生成新值
    
    Returns:
        Dict[str, Any]: 标准化后的响应，包含：
            - reply (str): 返回给用户的文本内容
            - actions (list): 快捷操作按钮列表，每个按钮包含 label 和 path
            - trace_id (str): 唯一追踪ID
    Example:
        >>> # 输入字符串
        >>> _normalize_chat_result("你好", "trace-123")
        {"reply": "你好", "actions": [], "trace_id": "trace-123"}
        
        >>> # 输入工具调用
        >>> _normalize_chat_result({"type": "tool_call", "tool": "navigate", "params": {"path": "/home"}})
        {"reply": "", "actions": [{"label": "前往页面", "path": "/home"}], "trace_id": "xxx"}
    """
    
    # ==================== 1. 基础格式转换 ====================
    # 确保 result 是字典格式
    # - 如果已经是 dict，直接使用
    # - 如果是 str 或其他类型，包装成 {"reply": str(result)}
    # - 如果是 None 或空，使用空字符串
    normalized = dict(result) if isinstance(result, dict) else {"reply": str(result or "")}
    # 确保 reply 字段存在（防止后续代码出现 KeyError）
    normalized.setdefault("reply", "")
    # ==================== 2. 处理 actions（快捷操作按钮）====================
    # 获取现有的 actions，如果不是列表则初始化为空列表
    actions = normalized.get("actions")
    if not isinstance(actions, list):
        actions = []
    # ----- 2.1 为工具调用添加快捷按钮 -----
    # 当返回结果是一个工具调用（而非最终回复）时，自动添加对应的操作按钮
    # 这样前端可以展示"前往页面"等快捷入口
    if normalized.get("type") == "tool_call":
        tool = str(normalized.get("tool") or "")
        params = normalized.get("params") if isinstance(normalized.get("params"), dict) else {}
        
        # 导航工具：添加页面跳转按钮
        if tool == "navigate" and params.get("path"):
            actions.append({
                "label": "前往页面", 
                "path": params["path"]
            })
        
        # 预约相关工具：添加"查看我的预约"按钮
        # 用户取消或查询预约后，可以直接跳转到预约列表页
        if tool in {"my_reservations", "cancel_reservation"}:
            actions.append({
                "label": "查看我的预约", 
                "path": "/pages/my-reservations/my-reservations"
            })
    
    # 将处理好的 actions 写回
    normalized["actions"] = actions
    
    # ==================== 3. 处理 trace_id（追踪ID）====================
    # trace_id 的优先级（从高到低）：
    # 1. result 中已有的 trace_id
    # 2. 函数参数传入的 trace_id
    # 3. 新生成的 trace_id
    #
    # trace_id 的作用：
    # - 关联用户的一次完整对话请求
    # - 便于日志查询和问题排查
    # - 支持全链路追踪
    normalized["trace_id"] = str(
        normalized.get("trace_id") or trace_id or _new_trace_id()
    )
    
    # ==================== 4. 返回标准化结果 ====================
    return normalized


def _llm_agent_decide(context: str, history: List[Dict[str, Any]], form: Dict[str, Any]) -> Dict[str, Any]:
    """
    LLM Agent 决策核心 - 让大语言模型决定下一步做什么
    这是 Agent 系统的"大脑"，负责：
    1. 分析当前对话上下文和历史
    2. 理解用户意图和已完成的操作
    3. 决定下一步调用哪个工具（或结束对话）
    4. 生成给用户的回复
    Args:
        context: 当前上下文，包含用户请求、上一步执行结果、当前表单状态等
        history: 历史执行记录，包含之前每一步的工具调用和结果
        form: 当前预约表单，记录用户已填写的预约信息
    Returns:
        Dict[str, Any]: 决策结果，包含：
            - tool (str): 要调用的工具名称，空字符串表示不调用工具
            - params (dict): 工具参数（可能不完整，后续会自动填充）
            - reply (str): 给用户的回复内容
            - done (bool): 是否完成任务（True 表示结束对话）
    """
    
    # ==================== 1. 降级检查 ====================
    # 如果没有配置 LLM API，无法使用此功能
    # 返回空字典，上层会使用规则引擎降级
    if not Config.LLM_API_KEY:
        return {}
    
    # ==================== 2. 工具定义 ====================
    # 定义所有可用工具及其参数要求
    # 这个定义会发给 LLM，让它知道有哪些能力可用
    # 
    # 字段说明：
    # - name: 工具名称
    # - required: 必需参数列表（不提供无法执行）
    # - optional: 可选参数列表（可以后续补充）
    tools = [

    # ===== 查询类（基础数据获取） =====
    {
        "name": "query_labs",  
        # 查询实验室列表（支持多条件筛选）
        # 用于“有哪些实验室 / 可用实验室”场景
        "required": [],
        "optional": ["date", "campus", "type", "participant_count"]
    },

    {
        "name": "query_schedule",  
        # 查询某天的实验室排期（占用情况）
        # 用于判断某一天是否空闲
        "required": ["date"],
        "optional": ["lab_id"]
    },

    {
        "name": "check_availability",  
        # 判断某个时间段是否可预约（强约束工具）
        # 用于避免冲突，是 create_reservation 前的关键校验
        "required": ["lab_id", "date", "start_time", "end_time"],
        "optional": []
    },


    # ===== 推荐类（AI智能能力） =====
    {
        "name": "recommend_time",  
        # 推荐最优预约时间段（基于排期计算）
        # 用于“什么时候有空 / 推荐时间”
        "required": ["date"],
        "optional": ["lab_id", "preference"]   # preference: 上午/下午
    },

    {
        "name": "recommend_lab",  
        # 推荐最合适的实验室（基于人数/类型/校区）
        # 用于“帮我推荐一个实验室”
        "required": ["date"],
        "optional": ["participant_count", "type", "campus"]
    },


    # ===== 实验室信息类 =====
    {
        "name": "get_lab_detail",  
        # 获取实验室详细信息（设备 / 描述 / 容量等）
        # 用于解释性回答（增强智能感）
        "required": ["lab_id"],
        "optional": []
    },


    # ===== 预约操作类（核心业务） =====
    {
        "name": "create_reservation",  
        # 创建预约（最终执行动作）
        # Agent最终目标之一
        "required": [
            "lab_id",
            "date",
            "start_time",
            "end_time",
            "participant_count",
            "purpose"
        ],
        "optional": []
    },

    {
        "name": "update_reservation",  
        # 修改已有预约
        # 支持“帮我改时间”这种高级交互
        "required": ["reservation_id"],
        "optional": ["date", "start_time", "end_time"]
    },

    {
        "name": "cancel_reservation",  
        # 取消预约
        # 支持完整生命周期管理
        "required": ["reservation_id"],
        "optional": []
    },

    {
        "name": "my_reservations",  
        # 查询当前用户的预约记录
        # 用于“我的预约”
        "required": [],
        "optional": []
    },


    # ===== 规则解释类（RAG能力） =====
    {
        "name": "explain_rules",  
        # 解释实验室预约规则
        # 用于“为什么不能预约 / 有什么限制”
        "required": [],
        "optional": ["question"]
    },


    # ===== 前端自动化（Agent核心能力） =====
    {
        "name": "navigate",  
        # 页面跳转（小程序路由）
        # AI驱动UI行为
        "required": ["path"],
        "optional": []
    },

    {
        "name": "fill_form",  
        # 自动填写预约表单
        # 实现“AI帮你填表”
        "required": ["form"],
        "optional": []
    },

    {
        "name": "submit_form",  
        # 自动提交表单
        # 实现“AI帮你完成预约”（关键一步）
        "required": [],
        "optional": []
    },
]
    
    # ==================== 3. 构建提示词 ====================
    # 将系统状态、工具定义、历史记录等信息组装成提示词
    # LLM 会根据这些信息做出决策
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
    
    # ==================== 4. 调用 LLM ====================
    try:
        # 调用 LLM API，temperature=0 确保输出确定性（相同输入得到相同输出）
        content = _call_llm_messages(
            [
                {"role": "system", "content": "你是严格 JSON 输出助手。"},  # 系统提示：要求输出 JSON
                {"role": "user", "content": prompt},                        # 用户提示：包含所有上下文
            ],
            temperature=0,  # 温度设为0，减少随机性，确保决策稳定
        )
        
        # ==================== 5. 解析 LLM 响应 ====================
        # 尝试将 LLM 输出解析为 JSON
        parsed = _safe_json_loads(content) or {}
        
        # 提取工具名称并验证
        tool = str(parsed.get("tool") or "").strip()
        # print("工具：")
        # print(tool)
        # 验证工具是否存在（防止 LLM 幻觉，输出不存在的工具）
        if tool and tool not in AGENT_TOOL_SCHEMAS:
            tool = ""  # 工具不存在，清空
        
        # ==================== 6. 返回标准化决策 ====================
        return {
            "tool": tool,                                              # 要调用的工具
            "params": _normalize_params_shape(parsed.get("params")),   # 工具参数
            "reply": str(parsed.get("reply") or "").strip(),           # 给用户的回复
            "done": bool(parsed.get("done", False)),                   # 是否完成
        }
    
    # ==================== 7. 异常处理 ====================
    # 任何异常（网络、解析、超时等）都返回空决策
    # 上层会使用规则引擎降级，保证系统可用性
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


def _tool_reply_prefer_facts(
    tool: str, tool_result: Dict[str, Any], planner_reply: str, params: Dict[str, Any]
) -> str:
    factual = str(tool_result.get("data") or "").strip()
    if tool in {"query_labs", "query_schedule", "recommend_time"}:
        # For date/schedule related tools, trust tool output first.
        if factual:
            return factual
        return planner_reply or "?????"
    if factual:
        return factual
    return planner_reply or "?????"


def _auto_fill_params(tool: str, user, params: Dict[str, Any], form: Dict[str, Any], text: str, session: Dict[str, Any]) -> Dict[str, Any]:
    merged = _extract_form_from_text(user, text, form, session)
    pref = _detect_preference(text)
    if pref:
        merged["preference"] = pref
    raw = dict(params or {})
    for key in ["date", "participant_count", "start_time", "end_time", "purpose", "campus", "type", "lab_id", "preference"]:
        if not raw.get(key) and merged.get(key):
            raw[key] = merged[key]
    if tool == "cancel_reservation" and not raw.get("reservation_id"):
        rid = _detect_reservation_id_or_choice(text, session)
        if rid:
            raw["reservation_id"] = rid
    # Double safety: force relative date before tool execution.
    relative_date = _resolve_relative_date(text)
    if relative_date:
        raw["date"] = relative_date
    sanitized = _sanitize_tool_params(tool, raw)
    trace_id = str(session.get("_debug_trace_id") or "")
    _debug_log(trace_id, "auto_fill_params", tool=tool, in_params=params, out_params=sanitized)
    return sanitized



def _run_tool(tool: str, params: Dict[str, Any], user, session: Dict[str, Any]) -> Dict[str, Any]:
    trace_id = str(session.get("_debug_trace_id") or "")
    _debug_log(trace_id, "run_tool_enter", tool=tool, params=params)
    # ===== 参数校验 =====
    missing = _missing_required_tool_fields(tool, params)
    if missing:
        _debug_log(trace_id, "run_tool_missing_fields", tool=tool, missing=missing)
        return _tool_result(
            tool,
            False,
            _missing_fields_hint(tool, missing),
            error_code="missing_fields",
            error_message="missing required params",
        )

    # ===== 查询实验室 =====
    if tool == "query_labs":
        labs = _query_labs(
            params.get("date") or "",
            params.get("campus") or "",
            params.get("type") or "",
            _safe_int(params.get("participant_count")),
        )
        session["last_labs"] = [{"id": lab.id, "name": lab.lab_name} for lab in labs[:8]]

        return _tool_result(tool, True, _labs_to_text(labs), extra={"labs_count": len(labs)})

    # ===== 查询排期 =====
    if tool == "query_schedule":
        result = _query_schedule(params.get("date"), _safe_int(params.get("lab_id")))
        return _tool_result(
            tool,
            bool(result.get("ok")),
            _schedule_result_to_text(result),
            error_code="query_failed" if not result.get("ok") else "",
            raw=result,
        )

    # ===== 检查是否可预约 =====
    if tool == "check_availability":
        lab_id = _safe_int(params.get("lab_id"))
        lab = Laboratory.query.get(lab_id)
        if not lab:
            return _tool_result(tool, False, "实验室不存在", error_code="not_found")

        schedule = get_lab_schedule(lab, datetime.strptime(params["date"], "%Y-%m-%d").date())
        rows = schedule.get("reservations") or []

        st = _to_minutes(params["start_time"])
        et = _to_minutes(params["end_time"])

        for r in rows:
            s = _to_minutes(r["start_time"][:5])
            e = _to_minutes(r["end_time"][:5])
            if not (et <= s or st >= e):
                return _tool_result(tool, False, "该时间段已被占用", error_code="conflict")

        return _tool_result(tool, True, "该时间段可以预约")

    # ===== 推荐时间 =====
    if tool == "recommend_time":
        reply, pick = _recommend_time(
            params.get("date"),
            _safe_int(params.get("lab_id")),
            str(params.get("preference") or ""),
        )
        return _tool_result(
            tool,
            pick is not None,
            reply,
            error_code="no_slot" if pick is None else "",
            extra={"pick": pick},
        )

    # ===== 推荐实验室 =====
    if tool == "recommend_lab":
        labs = _query_labs(
            params.get("date"),
            params.get("campus"),
            params.get("type"),
            _safe_int(params.get("participant_count")),
        )
        if not labs:
            return _tool_result(tool, False, "没有合适实验室", error_code="not_found")

        lab = labs[0]
        return _tool_result(
            tool,
            True,
            f"推荐实验室：{lab.lab_name}（容量{lab.capacity}）",
            extra={"lab_id": lab.id},
        )

    # ===== 获取实验室详情 =====
    if tool == "get_lab_detail":
        lab = Laboratory.query.get(_safe_int(params.get("lab_id")))
        if not lab:
            return _tool_result(tool, False, "实验室不存在", error_code="not_found")

        text = f"{lab.lab_name}，容量{lab.capacity}，位置{lab.location}"
        return _tool_result(tool, True, text, raw={"lab_id": lab.id})

    # ===== 创建预约 =====
    if tool == "create_reservation":
        payload = {
            "lab_id": _safe_int(params.get("lab_id")),
            "reservation_date": params.get("date"),
            "start_time": params.get("start_time"),
            "end_time": params.get("end_time"),
            "participant_count": _safe_int(params.get("participant_count")) or 1,
            "purpose": params.get("purpose"),
        }

        lab = Laboratory.query.get(payload["lab_id"])
        if not lab:
            return _tool_result(tool, False, "实验室不存在", error_code="not_found")

        payload["campus_id"] = lab.campus_id

        try:
            created = create_reservation(user, payload)
            _reset_form(session)
            return _tool_result(
                tool,
                True,
                f"预约成功：{created.get('lab_name')} {created.get('reservation_date')} "
                f"{str(created.get('start_time'))[:5]}-{str(created.get('end_time'))[:5]}",
                raw=created,
            )
        except AppError as exc:
            return _tool_result(tool, False, f"预约失败：{exc.message}", error_code="business_rule")

    # ===== 修改预约 =====
    if tool == "update_reservation":
        reservation = Reservation.query.get(_safe_int(params.get("reservation_id")))
        if not reservation:
            return _tool_result(tool, False, "预约不存在", error_code="not_found")

        if params.get("date"):
            reservation.reservation_date = params["date"]
        if params.get("start_time"):
            reservation.start_time = params["start_time"]
        if params.get("end_time"):
            reservation.end_time = params["end_time"]

        return _tool_result(tool, True, "预约已更新")

    # ===== 我的预约 =====
    if tool == "my_reservations":
        rows = Reservation.query.filter_by(user_id=user.id).limit(8).all()
        if not rows:
            return _tool_result(tool, True, "暂无预约记录")

        session["last_reservations"] = [{"id": r.id} for r in rows]

        text = "\n".join([
            f"{r.id} | {r.lab.lab_name if r.lab else '-'} | {r.reservation_date}"
            for r in rows
        ])

        return _tool_result(tool, True, text)

    # ===== 取消预约 =====
    if tool == "cancel_reservation":
        reservation = Reservation.query.get(_safe_int(params.get("reservation_id")))
        if not reservation:
            return _tool_result(tool, False, "预约不存在", error_code="not_found")

        try:
            updated = cancel_reservation(user, reservation)
            return _tool_result(tool, True, f"已取消预约 {updated.get('id')}", raw=updated)
        except AppError as exc:
            return _tool_result(tool, False, f"取消失败：{exc.message}")

    # ===== 规则解释 =====
    if tool == "explain_rules":
        return _tool_result(tool, True, _rules_context())

    # ===== 页面跳转 =====
    if tool == "navigate":
        return _tool_result(tool, True, _normalize_nav_path(params.get("path")))

    # ===== 自动填表 =====
    if tool == "fill_form":
        return _tool_result(tool, True, "已填写表单", raw={"form": params.get("form")})

    # ===== 提交表单 =====
    if tool == "submit_form":
        return _tool_result(tool, True, "表单已提交")

    _debug_log(trace_id, "run_tool_unknown", tool=tool)
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


# 开始
#   ↓
# LLM API 可用？ ─No→ 规则引擎降级
#   ↓ Yes
# 初始化状态 (context, history, form)
#   ↓
# ┌─────────────────────────────────────┐
# │         Agent 循环 (最多5步)         │
# ├─────────────────────────────────────┤
# │  1. LLM 决策 (工具/参数/done)        │
# │  2. 检查终止条件                     │
# │  3. 自动填充参数                     │
# │  4. 执行工具                         │
# │  5. 记录历史                         │
# │  6. 检测重复调用                     │
# │  7. 特殊工具快速返回                 │
# │  8. 更新上下文继续循环               │
# └─────────────────────────────────────┘
#   ↓
# 达到最大步数 → 规则引擎降级
#   ↓
# 返回结果
def _agent_loop(user, user_input: str, session: Dict[str, Any], trace_id: str) -> Any:
    """
    Agent 主循环 - LLM 驱动的智能对话处理核心
    这是整个 Agent 系统的决策和执行引擎，负责：
    1. 使用 LLM 决策下一步调用哪个工具
    2. 自动填充缺失的参数（从用户输入和表单中）
    3. 执行工具并处理结果
    4. 循环执行直到任务完成或达到限制
    
    循环终止条件：
    - LLM 标记 done=true 且无工具调用
    - 没有可用的工具
    - 同一工具重复调用超过限制
    - 达到最大步数限制
    - 遇到无法恢复的错误
    
    Args:
        user: 当前用户对象
        user_input: 用户原始输入文本
        session: 用户会话数据（包含表单、历史等）
        trace_id: 追踪ID，用于日志关联
    
    Returns:
        Any: 标准化响应（经过 _normalize_chat_result 处理）
    """
    
    # ==================== 1. 降级检查 ====================
    # 如果 LLM API 未配置，直接使用规则引擎降级
    # 这是系统的第一道防线
    session["_debug_trace_id"] = trace_id
    _debug_log(trace_id, "agent_loop_start", user_input=user_input)
    if not Config.LLM_API_KEY:
        _debug_log(trace_id, "fallback_rule", reason="missing_llm_api_key")
        return _normalize_chat_result(
            _fallback_rule_chat(user, user_input, session), 
            trace_id
        )
    
    # ==================== 2. 初始化循环状态 ====================
    context = user_input                    # 上下文（逐步累积）
    history: List[Dict[str, Any]] = []     # 执行历史（供 LLM 决策参考）
    
    # 获取当前预约表单（用户已填写的信息）
    form = dict(session.get("reservation_form") or {})
    
    # 从用户输入中提取信息，更新表单
    form = _extract_form_from_text(user, user_input, form, session)
    session["reservation_form"] = form
    _debug_log(trace_id, "form_initialized", form=form)
    
    # 工具重复调用检测（防止死循环）
    last_tool, same_tool_count = "", 0
    
    # ==================== 3. Agent 主循环 ====================
    # 循环执行，最多 MAX_AGENT_STEPS 步
    for step in range(1, MAX_AGENT_STEPS + 1):
        
        # ----- 3.1 LLM 决策：下一步做什么 -----
        # 调用 LLM 分析当前状态，决定调用哪个工具或结束
        decision = _llm_agent_decide(context, history, form)
        tool = str(decision.get("tool") or "").strip()
        params = _normalize_params_shape(decision.get("params"))
        planner_reply = str(decision.get("reply") or "").strip()
        done = bool(decision.get("done", False))
        _debug_log(trace_id, "llm_decision", step=step, tool=tool, done=done, params=params)
        
        # ----- 3.2 终止条件判断 -----
        # 情况1：LLM 认为任务完成且不需要调用工具
        if done and not tool:
            return {
                "reply": planner_reply or "处理完成。",
                "actions": [],
                "trace_id": trace_id
            }
        
        # 情况2：LLM 没有选择任何工具（可能无法理解）
        if not tool:
            return {
                "reply": planner_reply or "请补充更多信息。",
                "actions": [],
                "trace_id": trace_id
            }
        
        # ----- 3.3 参数自动填充 -----
        # 从用户输入和表单中补充缺失的参数
        # 例如：用户说了"明天下午3点"，自动填充 date、start_time
        params = _auto_fill_params(tool, user, params, form, context, session)
        _debug_log(trace_id, "params_filled", step=step, tool=tool, params=params)
        
        # 将成功填充的参数同步回表单（持久化）
        for key in ["date", "participant_count", "start_time", "end_time", 
                    "purpose", "campus", "type", "lab_id"]:
            if params.get(key) not in [None, ""]:
                form[key] = params.get(key)
        session["reservation_form"] = form
        
        # ----- 3.4 执行工具 -----
        tool_result = _run_tool(tool, params, user, session)
        _debug_log(
            trace_id,
            "tool_executed",
            step=step,
            tool=tool,
            ok=bool(tool_result.get("ok")),
            error_code=tool_result.get("error_code"),
            data_preview=str(tool_result.get("data") or "")[:120],
        )
        
        # ----- 3.5 记录执行历史 -----
        # 供 LLM 在下一步决策时参考
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
        
        # ----- 3.6 工具重复调用检测 -----
        # 防止 Agent 陷入同一工具的循环调用
        same_tool_count = same_tool_count + 1 if tool == last_tool else 1
        last_tool = tool
        if same_tool_count > MAX_TOOL_REPEAT_STEPS:
            return {
                "reply": "同一步骤重复尝试过多次。请补充更具体信息后我再继续。",
                "actions": [],
                "trace_id": trace_id
            }
        
        # ==================== 4. 特殊工具快速返回 ====================
        
        # ----- 4.1 导航工具：立即跳转页面 -----
        if tool == "navigate":
            return {
                "reply": planner_reply or "我带你进入对应页面。",
                "actions": [{"label": "前往页面", "path": str(tool_result.get("data") or "/pages/agent/agent")}],
                "trace_id": trace_id
            }
        
        # ----- 4.2 预约查询/取消：返回结果并提供快捷入口 -----
        if tool in {"my_reservations", "cancel_reservation"}:
            return {
                "reply": str(tool_result.get("data") or "处理完成。"),
                "actions": [{"label": "查看我的预约", "path": "/pages/my-reservations/my-reservations"}],
                "trace_id": trace_id
            }
        
        # ----- 4.3 创建预约：成功或失败都立即返回 -----
        if tool == "create_reservation":
            if tool_result.get("ok"):
                return {
                    "reply": f"已帮你完成预约: {tool_result.get('data')}",
                    "actions": [{"label": "查看我的预约", "path": "/pages/my-reservations/my-reservations"}],
                    "trace_id": trace_id
                }
            return {
                "reply": str(tool_result.get("data") or "预约失败。"),
                "actions": [],
                "trace_id": trace_id
            }
        
        # ----- 4.4 LLM 标记完成：返回结果 -----
        if done:
            final_reply = _tool_reply_prefer_facts(tool, tool_result, planner_reply, params)
            _debug_log(trace_id, "done_return", step=step, reply_preview=final_reply[:120])
            return {
                "reply": final_reply,
                "actions": [],
                "trace_id": trace_id
            }
        
        # ----- 4.5 不可恢复的错误：立即返回 -----
        # 这些错误类型表示无法通过继续循环解决
        if not tool_result.get("ok") and tool_result.get("error_code") in {
            "missing_fields",   # 缺少必需参数
            "invalid_params",   # 参数无效
            "not_found",        # 资源不存在
            "business_rule"     # 违反业务规则
        }:
            return {
                "reply": str(tool_result.get("data") or "处理失败。"),
                "actions": [],
                "trace_id": trace_id
            }
        
        # ==================== 5. 继续下一轮循环 ====================
        # 更新上下文，让 LLM 了解上一步的执行结果
        # 这样 LLM 可以基于实际情况做出下一步决策
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
    
    # ==================== 6. 超过最大步数 ====================
    # 如果循环超过 MAX_AGENT_STEPS 仍未完成，降级到规则引擎
    return _normalize_chat_result(
        _fallback_rule_chat(user, user_input, session), 
        trace_id
    )

def chat(user, message):
    """
    对话主入口函数 - 处理用户消息并返回 Agent 响应
    这是整个 Agent 系统的统一入口，负责：
    1. 消息预处理和验证
    2. 用户会话管理
    3. 意图路由（实验室相关 / 通用问题）
    4. 错误处理和降级方案
    Args:
        user: 用户对象，包含用户信息（必须有 id 属性或字典格式）
        message: 用户输入的消息文本
    Returns:
        Dict: 标准化响应，包含以下字段：
            - reply (str): 返回给用户的回复文本
            - actions (list): 快捷操作按钮列表（如页面跳转）
            - trace_id (str): 追踪ID，用于日志和问题排查
    Example:
        >>> response = chat(user, "帮我查一下明天下午的实验室")
        >>> print(response["reply"])
        "我来帮你查排期..."
    """
    # ==================== 1. 消息预处理 ====================
    # 将用户输入转换为字符串并去除首尾空格
    text = str(message or "").strip()
    
    # 生成唯一的追踪ID，用于全链路追踪
    trace_id = _new_trace_id()
    _debug_log(trace_id, "chat_received", message=text)
    
    # 处理空消息：返回引导提示
    if not text:
        return {
            "reply": "你可以让我查实验室、查排期、创建预约、取消预约，或查看我的预约。",
            "actions": [],
            "trace_id": trace_id
        }
    
    # ==================== 2. 用户身份验证 ====================
    # 尝试从 user 对象中获取用户ID
    # 支持两种格式：对象属性（user.id）或字典（user["id"]）
    user_id = getattr(user, "id", None)
    if not user_id and isinstance(user, dict):
        user_id = user.get("id")
    
    # 用户信息异常时拒绝处理
    if not user_id:
        _debug_log(trace_id, "chat_rejected", reason="invalid_user")
        return {
            "reply": "用户信息异常，暂时无法处理请求。",
            "actions": [],
            "trace_id": trace_id
        }
    
    # ==================== 3. 会话初始化 ====================
    # 获取或创建用户会话（包含预约表单、历史记录等）
    # 会自动清理过期会话（超过 SESSION_TTL_MINUTES 分钟无操作）
    session = _clean_session(user_id)
    
    # ==================== 4. 意图路由与处理 ====================
    try:
        # ----- 4.1 退出预约流程（最高优先级）-----
        # 检查用户是否想要退出当前的预约创建流程
        # 关键词：不需要预约、不用预约、先不预约、不约了等
        if _is_cancel_flow_message(text):
            _debug_log(trace_id, "route", target="cancel_flow")
            _reset_form(session)           # 清空预约表单
            _save_session(user_id, session) # 保存会话状态
            return _normalize_chat_result(
                "好的，已退出当前预约流程。后续你可以继续让我查实验室、排期或帮你预约。",
                trace_id
            )
        
        # ----- 4.2 实验室相关问题 vs 通用问题 -----
        # 判断用户问题是否与实验室预约相关
        # 相关关键词：实验室、预约、排期、空闲、lab、schedule等
        if _is_lab_related(text):
            _debug_log(trace_id, "route", target="agent_loop")
            # 实验室相关问题：Agent 智能处理
            # 使用 LLM 驱动的 Agent 循环处理复杂预约场景
            # Agent 会自动决策调用哪个工具、补充缺失信息等
            try:
                # 首选方案：LLM Agent 循环（智能决策）
                result = _agent_loop(user, text, session, trace_id)
            except Exception:
                _debug_log(trace_id, "agent_loop_exception_fallback", reason="agent_loop_exception")
                # 降级方案1：规则引擎（基于正则匹配的简单处理）
                try:
                    result = _fallback_rule_chat(user, text, session)
                except Exception:
                    _debug_log(trace_id, "fallback_exception_general_llm", reason="fallback_exception")
                    # 降级方案2：通用 LLM 兜底
                    result = _call_general_llm(user, text)
            
            # 保存会话（更新最后操作时间）
            _save_session(user_id, session)
            
            # 标准化返回格式（统一添加 trace_id 和 actions）
            return _normalize_chat_result(result, trace_id)
        
        # ----- 4.3 通用问题（包括日期时间、天气、新闻、闲聊等）-----
        # 所有非实验室相关问题统一交给通用 LLM 处理
        # 通用 LLM 本身就能回答日期时间、天气、计算等问题
        _debug_log(trace_id, "route", target="general_llm")
        result = _call_general_llm(user, text)
        _save_session(user_id, session)
        return _normalize_chat_result(result, trace_id)
    
    # ==================== 5. 异常处理 ====================
    # 捕获所有未预期的异常，返回友好错误提示
    except Exception as exc:
        return {
            "reply": f"系统处理失败: {str(exc)}",
            "actions": [],
            "trace_id": trace_id
        }

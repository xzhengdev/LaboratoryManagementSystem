import json
import re
from datetime import date, datetime, time, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4
from zoneinfo import ZoneInfo
import requests
from app.config import Config
from app.models import Laboratory, Reservation
from app.services.agent_debug import debug_log as _debug_log
from app.services.agent_helpers import (
    contains_any as _contains_any,
    is_abab_loop as _is_abab_loop,
    normalize_params_shape as _normalize_params_shape,
    safe_int as _safe_int,
    safe_json_loads as _safe_json_loads,
    to_minutes as _to_minutes,
    tool_call as _tool_call,
    tool_result as _tool_result,
)
from app.services.agent_rules import (
    build_followup_question as _build_followup_question,
    missing_fields_hint as _missing_fields_hint,
)
from app.services.agent_session import (
    clean_session as _session_clean,
    reset_form as _session_reset_form,
    save_session as _session_save,
)
from app.services.reservation_service import cancel_reservation, create_reservation, get_lab_schedule
from app.utils.exceptions import AppError
from app.extensions import db  # 如果你的项目不是这个路径，改成你自己的 db 导入

ACTIVE_RESERVATION_STATUSES = {"pending", "approved"} #预约状态控制，判断预约时间是否冲突
SESSION_TTL_MINUTES = 10                              #用户会话保留 10 分钟
MAX_AGENT_STEPS = 5
MAX_TOOL_REPEAT_STEPS = 2
MAX_HISTORY_SUMMARY_CHARS = 280
DEFAULT_AGENT_TIMEZONE = "Asia/Shanghai"
FOLLOWUP_CONTEXT_TTL_SECONDS = 600
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
        "optional": ["participant_count", "type", "campus", "preference"],
        "description": "根据日期、人数、实验室类型、校区和时间偏好等条件，为用户推荐最合适的实验室。",
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

# ==================== 会话存储 ====================
AGENT_SESSIONS: Dict[int, Dict[str, Any]] = {}

# ==================== 获取当前时间（带时区） ====================
def _localized_now() -> datetime:
    tz_name = str(getattr(Config, "AGENT_TIMEZONE", DEFAULT_AGENT_TIMEZONE) or DEFAULT_AGENT_TIMEZONE)
    try:
        return datetime.now(ZoneInfo(tz_name))
    except Exception:
        return datetime.now()
# ==================== 获取当前时间（无时区） ====================
def _now() -> datetime:
    return datetime.now()
# ==================== 获取今天日期 ====================
def _today() -> date:
    return _localized_now().date()
# ==================== 生成追踪ID ====================
def _new_trace_id() -> str:
    return f"agt-{uuid4().hex[:12]}"

#=================================================================debug=================================
# 根据工具定义过滤并清洗参数，只保留合法字段并做类型转换
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

 # 检查工具调用时缺失的必填参数字段
def _missing_required_tool_fields(tool: str, params: Dict[str, Any]) -> List[str]:
    schema = AGENT_TOOL_SCHEMAS.get(tool) or {}
    missing = []
    for key in schema.get("required") or []:
        value = params.get(key)
        if value is None or value == "":
            missing.append(key)
    return missing

 # 获取预约规则上下文（优先读取配置，否则使用默认规则）
def _rules_context() -> str:
    text = str(getattr(Config, "AGENT_RULES_CONTEXT", "") or "")
    if text.strip():
        return text
    return (
        "实验室预约规则: 预约必须在实验室开放时间内，开始时间早于结束时间; "
        "预约开始至少晚于当前时间30分钟，预约日期不能超过未来7天; "
        "参与人数不可超过实验室容量; 同一用户不能重叠预约。"
        "如果当前工具结果已经足以直接回答用户问题，不要再调用其他工具，直接 done=true。"
        "对“查询空闲实验室/查看实验室列表”这类请求，query_labs 成功后通常即可结束。"
        "不要为了重复验证而再次调用 query_schedule，除非用户明确要求查看排期。"
    )

# 从规则文本中提取“需提前多少天预约”的限制
def _extract_min_advance_days(ctx: str) -> int:
    m = re.search(r"提前\s*(\d+)\s*天", ctx)
    if m:
        return int(m.group(1))
    return 0

 # 判断规则中是否禁止重复或重叠预约
def _forbid_duplicate(ctx: str) -> bool:
    return "重叠预约" in ctx or "重复预约" in ctx

def _call_llm_messages(messages: List[Dict[str, str]], temperature: float = 0.1) -> str:
    """
    调用 LLM API 的核心函数 - 与大语言模型通信的统一接口
    这是整个系统中与 LLM 通信的唯一入口
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
    # timeout=60: 60秒超时限制，防止长时间阻塞
    # 如果超时，requests 会抛出 Timeout 异常
    resp = requests.post(
        Config.LLM_BASE_URL,  # API 端点地址
        headers=headers,
        json=payload,         # 自动将 dict 序列化为 JSON
        timeout=160
    )
    
    # ==================== 5. 检查响应状态 ====================
    # raise_for_status() 会在 HTTP 状态码不是 2xx 时抛出异常
    # 例如：401 Unauthorized, 429 Too Many Requests, 500 Internal Error
    resp.raise_for_status()
    
    # ==================== 6. 解析响应并提取内容 ====================
    # 将 JSON 字符串解析为 Python 字典
    data = resp.json()
    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("llm response missing choices")
    # 提取第一 choice 的 message.content
    # 响应格式遵循 OpenAI Chat Completion API
    # data["choices"][0]["message"]["content"] 是标准路径
    message = choices[0].get("message") or {}
    content = message.get("content")
    if content is None:
        raise RuntimeError("llm response missing content")

    return str(content).strip()

# 当 Agent 不走工具流程时，用这个函数直接和大模型聊天
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
    return _session_clean(AGENT_SESSIONS, user_id, _now, SESSION_TTL_MINUTES)


def _save_session(user_id: int, session: Dict[str, Any]) -> None:
    _session_save(AGENT_SESSIONS, user_id, session, _now)

# 把当前会话里的预约表单恢复成“初始空状态”
def _reset_form(session: Dict[str, Any]) -> None:
    _session_reset_form(session)

# 识别“今天/明天/后天”等相对日期，并转换为对应的天数偏移
def _relative_day_offset(text: str) -> Optional[int]:
    msg = text or ""
    if "后天" in msg:
        return 2
    if "明天" in msg:
        return 1
    if "今天" in msg:
        return 0
    return None

# 将相对日期转换为具体日期字符串（YYYY-MM-DD）
def _resolve_relative_date(text: str) -> Optional[str]:
    offset = _relative_day_offset(text)
    if offset is None:
        return None
    return (_today() + timedelta(days=offset)).isoformat()

# 从用户输入中提取日期，支持相对日期、标准日期和中文日期格式
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

 # 将中文时间表达规范化为 24 小时制时间字符串（HH:MM）
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

# 从用户输入中提取时间范围，支持“14:00-16:00”和“下午2点到4点”两种格式
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
    m3 = re.search(r"(\d{1,2}:\d{2})\s*(?:开始|开[始场]|起)", msg)
    if m3:
        return m3.group(1), None
    m4 = re.search(r"(上午|下午|晚上|中午)?\s*(\d{1,2})点(?:([0-5]?\d)分?)?\s*(?:开始|开[始场]|起)", msg)
    if m4:
        p, h, mm = m4.groups()
        return _normalize_clock(int(h), int(mm or 0), p), None
    return None, None


def _detect_duration_minutes(text: str) -> Optional[int]:
    msg = text or ""
    m_hour = re.search(r"(\d{1,2})\s*(?:个)?小时", msg)
    if m_hour:
        return int(m_hour.group(1)) * 60
    if "半小时" in msg:
        return 30
    m_minute = re.search(r"(\d{1,3})\s*分钟", msg)
    if m_minute:
        return int(m_minute.group(1))
    return None


def _add_minutes(hhmm: str, delta_minutes: int) -> str:
    base = _to_minutes(hhmm)
    total = max(0, min(23 * 60 + 59, base + delta_minutes))
    return f"{total // 60:02d}:{total % 60:02d}"

 # 从用户输入中提取参与人数
def _detect_participant_count(text: str) -> Optional[int]:
    m = re.search(r"(\d{1,3})\s*人", text or "")
    if m:
        return int(m.group(1))
    return None

# 从用户输入中提取预约用途说明
def _detect_purpose(text: str) -> Optional[str]:
    msg = (text or "").strip()
    m = re.search(r"(?:用途|用于|目的)[:：]?\s*(.+)$", msg)
    if m:
        return m.group(1).strip()[:120]
    for key in ["课程实验", "项目讨论", "上课", "答辩", "开会", "做实验", "做项目"]:
        if key in msg:
            if key == "做实验":
                return "课程实验"
            if key == "做项目":
                return "项目讨论"
            return key
    return None

# 从用户输入中识别校区信息
def _detect_campus(text: str) -> str:
    msg = text or ""
    
    patterns = [
        r"(海淀|丰台|海南)校区",  # 完整：丰台校区
        r"(海淀|丰台|海南)的",   # 口语：丰台的
        r"(海淀|丰台|海南)(?= |$|，|。)",  # 单独的"丰台"
        r"校本部",
    ]
    
    for pattern in patterns:
        m = re.search(pattern, msg)
        if m:
            campus = m.group(1) if m.group(1) else m.group(0)
            # 标准化返回
            if campus in ["海淀", "丰台", "海南"]:
                return f"{campus}校区"
            return campus
    
    return ""


def _detect_type(text: str) -> str:
    msg = text or ""
    for key in ["计算机", "化学", "物理", "生物", "电子", "语音", "AI", "人工智能"]:
        if key.lower() in msg.lower():
            return key
    return ""


def _detect_preference(text: str) -> str:
    msg = text or ""
    if "晚上" in msg or "晚间" in msg:
        return "晚上"
    if "下午" in msg:
        return "下午"
    if "上午" in msg or "早上" in msg:
        return "上午"
    return ""

def _can_treat_as_choice(session: Dict[str, Any], choice_type: str) -> bool:
    last_choice_type = str(session.get("last_choice_type") or "")
    if choice_type == "lab":
        return last_choice_type == "lab_list" and bool(session.get("last_labs"))
    if choice_type == "reservation":
        return last_choice_type == "reservation_list" and bool(session.get("last_reservations"))
    return False

def _detect_lab_id_or_choice(text: str, session: Dict[str, Any]) -> Optional[int]:
    msg = (text or "").strip()

    m = re.search(r"(?:实验室ID|lab_id|ID)[:：]?\s*(\d+)", msg, re.IGNORECASE)
    if m:
        return int(m.group(1))

    form = session.get("reservation_form") if isinstance(session.get("reservation_form"), dict) else {}
    current_lab_id = _safe_int((form or {}).get("lab_id"))
    if current_lab_id is not None and re.search(r"(这个实验室|该实验室|就这个|就它|那个实验室|推荐的那个)", msg):
        return current_lab_id

    labs = session.get("last_labs") or []

    idx_map = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5}
    choice_idx: Optional[int] = None
    m_idx = re.search(r"第\s*([1-9]|[一二三四五])\s*个", msg)
    if m_idx:
        token = m_idx.group(1)
        choice_idx = int(token) if token.isdigit() else idx_map.get(token)
    elif "第一个" in msg or "第1个" in msg or "第1间" in msg:
        choice_idx = 1
    elif "第二个" in msg or "第2个" in msg:
        choice_idx = 2
    elif "第三个" in msg or "第3个" in msg:
        choice_idx = 3

    # 只有在刚展示过实验室列表时，才把纯数字解释为“选第几个”
    if _can_treat_as_choice(session, "lab") and re.fullmatch(r"\d{1,2}", msg):
        idx = int(msg)
        if 1 <= idx <= len(labs):
            return int(labs[idx - 1]["id"])

    if _can_treat_as_choice(session, "lab") and choice_idx is not None:
        if 1 <= choice_idx <= len(labs):
            return int(labs[choice_idx - 1]["id"])

    if _can_treat_as_choice(session, "lab") and re.search(r"^(这个|就它|就这个|那个|推荐的那个)$", msg):
        if labs:
            return int(labs[0]["id"])

    return None




# 这个函数是用来把用户的模糊表达（第几个）转成具体 reservation_id，方便后端执行操作
def _detect_reservation_id_or_choice(text: str, session: Dict[str, Any]) -> Optional[int]:
    msg = (text or "").strip()

    m = re.search(r"(?:reservation_id|预约ID|预约id|ID)[:：#\s]*(\d+)", msg, re.IGNORECASE)
    if m:
        return int(m.group(1))

    rows = session.get("last_reservations") or []
    idx_map = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5}
    choice_idx: Optional[int] = None
    m_idx = re.search(r"第\s*([1-9]|[一二三四五])\s*(?:个|条)", msg)
    if m_idx:
        token = m_idx.group(1)
        choice_idx = int(token) if token.isdigit() else idx_map.get(token)
    elif "第一个" in msg or "第1个" in msg or "第一条" in msg:
        choice_idx = 1

    # 只有在刚展示过预约列表时，才把纯数字解释为“选第几个”
    if _can_treat_as_choice(session, "reservation") and re.fullmatch(r"\d{1,2}", msg):
        idx = int(msg)
        if 1 <= idx <= len(rows):
            return int(rows[idx - 1]["id"])

    if _can_treat_as_choice(session, "reservation") and choice_idx is not None:
        if 1 <= choice_idx <= len(rows):
            return int(rows[choice_idx - 1]["id"])

    if _can_treat_as_choice(session, "reservation") and re.search(r"^(这个|这条|就这个|那个)$", msg):
        if rows:
            return int(rows[0]["id"])

    return None


# 让大模型从用户输入中提取预约表单字段（补全信息）
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
    if not msg:
        return "general"

    # 1. 先识别最高优先级动作
    if _contains_any(msg, [
        "取消当前预约", "退出预约", "结束预约", "停止预约",
        "不需要预约", "不用预约", "不约了", "算了不约了"
    ]):
        return "cancel_flow"

    if _contains_any(msg, [
        "取消预约", "撤销预约", "删除预约", "取消这个预约",
        "cancel reservation", "cancel_reservation"
    ]):
        return "cancel_reservation"

    if _contains_any(msg, [
        "修改预约", "更改预约", "调整预约", "改预约",
        "修改时间", "更改时间", "调整时间", "改时间",
        "改日期", "改实验室", "update reservation", "update_reservation"
    ]):
        return "update_reservation"

    if _contains_any(msg, [
        "我的预约", "我有哪些预约", "查看我的预约", "预约记录", "我的预约记录"
    ]):
        return "my_reservations"

    # 2. 规则 / 说明 / 原因
    if _contains_any(msg, [
        "为什么不能预约", "为什么约不了", "预约规则", "规则说明",
        "有什么限制", "预约要求", "预约条件", "规则是什么", "为什么冲突"
    ]):
        return "explain_rules"

    # 3. 页面跳转
    if _contains_any(msg, [
        "去预约页面", "去排期页面", "打开页面", "进入页面",
        "打开预约页", "打开实验室页面", "打开我的预约", "去我的预约"
    ]):
        return "navigate"

    # 4. 查询 / 推荐 / 检查
    if _contains_any(msg, [
        "推荐时间", "帮我推荐时间", "推荐时段", "哪个时间合适",
        "什么时候能约", "什么时候可以预约", "哪天有空"
    ]):
        return "recommend_time"

    if _contains_any(msg, [
        "推荐实验室", "帮我推荐实验室", "推荐一个实验室",
        "哪间实验室合适", "哪个实验室适合"
    ]):
        return "recommend_lab"

    if _contains_any(msg, [
        "排期", "查看排期", "实验室排期", "查排期",
        "当天排期", "空闲时段", "查询空闲时间"
    ]):
        return "query_schedule"

    if _contains_any(msg, [
        "能不能约", "是否可以预约", "可以预约吗", "有没有冲突",
        "时间冲突", "这个时间可以吗", "这个时间能约吗", "这个时段行吗"
    ]):
        return "check_availability"

    if _contains_any(msg, [
        "实验室详情", "实验室信息", "实验室介绍", "实验室位置",
        "实验室容量", "实验室设备", "这个实验室怎么样", "实验室在哪"
    ]):
        return "get_lab_detail"

    # 5. 创建预约
    if _contains_any(msg, [
        "我要预约", "帮我预约", "创建预约", "约实验室",
        "订实验室", "预约实验室", "创建一个预约", "我要预定", "帮我直接创建", "直接创建预约"
    ]):
        return "create_reservation"

    # 6. 查询实验室
    if _contains_any(msg, [
        "有哪些实验室", "查询实验室", "查实验室", "实验室列表",
        "可用实验室", "空闲实验室", "有哪些可用实验室", "找实验室"
    ]):
        return "query_labs"

    # 7. 表单类
    if _contains_any(msg, [
        "填写表单", "帮我填", "自动填", "填一下表单", "填表"
    ]):
        return "fill_form"

    if _contains_any(msg, [
        "提交表单", "确认提交", "提交吧", "帮我提交", "确认预约", "直接提交"
    ]):
        return "submit_form"

    return "general"

def _is_lab_related(text: str) -> bool:
    msg = (text or "").lower()
    keys = [
        # ===== 实验室基础词 =====
        "实验室", "lab", "实验间", "教室", "机房",
        # ===== 预约相关 =====
        "预约", "预定", "约", "约实验室", "订实验室", "创建预约",
        "取消预约", "修改预约", "更改预约", "调整预约", "预约记录",
        "我的预约", "预约列表", "预约信息", "预约详情",
        # ===== 排期/空闲相关 =====
        "排期", "schedule", "空闲", "有空", "没空", "空余",
        "是否空闲", "有没有空", "什么时候有空", "什么时候空",
        "空闲时间", "空闲时段", "可用时间", "可预约时间",
        "这个时间可以吗", "这个时间能约吗", "这个时段行吗",
        "是否可以预约", "能不能约", "有没有冲突", "时间冲突",
        # ===== 推荐相关 =====
        "推荐时间", "推荐实验室", "推荐一下", "帮我推荐",
        "推荐个时间", "推荐个实验室", "哪个实验室好",
        "适合的实验室", "哪个时间合适", "什么时间合适",
        # ===== 实验室信息相关 =====
        "实验室详情", "实验室信息", "实验室介绍", "实验室情况",
        "位置", "容量", "设备", "有什么设备", "在哪",
        "能坐多少人", "实验室类型",
        # ===== 时间表达 =====
        "今天", "明天", "后天", "上午", "下午", "晚上", "中午",
        "几点", "开始", "结束", "到", "至", "时段", "时间段",
        # ===== 条件筛选 =====
        "校区", "海淀", "丰台", "海南", "校本部",
        "计算机", "化学", "物理", "生物", "电子", "语音", "ai", "人工智能",
        # ===== 表单/页面交互 =====
        "填写表单", "自动填", "填表", "提交表单", "提交预约",
        "跳转", "打开页面", "进入页面", "去预约页面", "去排期页面",
        # ===== 规则说明 =====
        "预约规则", "规则", "限制", "规则说明", "预约要求",
        "为什么不能预约", "为什么约不了", "预约条件"
    ]
    return any(k in msg for k in keys)


def _is_lab_followup(text: str, session: Dict[str, Any]) -> bool:
    msg = (text or "").strip().lower()
    if str(session.get("last_domain") or "") != "lab":
        return False
    if not msg:
        return False

    # 只要本身明显还是实验室相关，直接认为是续接
    if _is_lab_related(msg):
        return True

    followup_keys = [
        # ===== 时间补充 =====
        "今天", "明天", "后天", "上午", "下午", "晚上", "中午", "早上",
        "几点", "开始", "结束", "到", "至", "时段", "时间段",
        "两点", "三点", "四点", "五点", "六点", "七点", "八点",
        "1点", "2点", "3点", "4点", "5点", "6点", "7点", "8点",

        # ===== 时长补充 =====
        "小时", "个小时", "分钟", "半小时", "一小时", "两小时", "三小时",

        # ===== 人数补充 =====
        "人", "个人",

        # ===== 用途补充 =====
        "用途", "用于", "目的", "做实验", "上课", "讨论", "答辩", "开会",

        # ===== 选择补充 =====
        "就这个", "这个", "这个实验室", "选这个", "选它", "要这个",
        "第一个", "第二个", "第三个", "第四个", "第五个",
        "第1个", "第2个", "第3个", "第4个", "第5个",

        # ===== 确认补充 =====
        "可以", "行", "好", "好的", "那就这个", "那这个吧", "就它吧",

        # ===== 校区/类型补充 =====
        "海淀", "丰台", "海南", "校本部",
        "计算机", "化学", "物理", "生物", "电子", "语音", "ai", "人工智能"
    ]

    if any(k in msg for k in followup_keys):
        return True
    # 纯数字，可能表示“选第几个”
    if re.search(r"^\d{1,2}$", msg):
        return True
    # 时间格式：14:00 / 14:00-16:00
    if re.search(r"\d{1,2}:\d{2}", msg):
        return True
    # 中文时间格式：下午2点 / 2点半
    if re.search(r"(上午|下午|晚上|中午|早上)?\s*\d{1,2}点", msg):
        return True
    # 中文日期格式：4月20日 / 2026-04-20
    if re.search(r"\d{1,2}月\d{1,2}日", msg):
        return True
    if re.search(r"20\d{2}-\d{1,2}-\d{1,2}", msg):
        return True
    return False


def _is_cancel_flow_message(text: str) -> bool:
    msg = (text or "").strip().lower()
    keys = [
        "不需要预约", "不用预约", "先不预约", "不约了", "取消当前预约", "退出预约",
        "结束预约", "停止预约", "先这样吧", "算了不约了", "不用继续了",
        "先取消这个流程", "不预约了", "先不弄了", "不用帮我约了"
    ]
    return any(k in msg for k in keys)

# def _is_date_time_question(text: str) -> bool:
#     msg = (text or "").strip().lower()
#     keys = [
#         "今天几号",
#         "今天是几号",
#         "今天几月几号",
#         "今天日期",
#         "明天几号",
#         "明天是几号",
#         "后天几号",
#         "昨天几号",
#         "几号",
#         "几月几日",
#         "星期几",
#         "周几",
#         "礼拜几",
#         "现在几点",
#         "现在时间",
#         "time",
#         "date",
#     ]
#     return any(k in msg for k in keys)

# def _resolve_date_target(text: str, today: date) -> date:
#     # 从用户输入中解析目标日期（支持相对日期、标准日期、中文日期及星期表达），解析失败则返回今天
#     msg = (text or "").strip()

#     # Relative date first.
#     if "大后天" in msg:
#         return today + timedelta(days=3)
#     if "后天" in msg:
#         return today + timedelta(days=2)
#     if "明天" in msg:
#         return today + timedelta(days=1)
#     if "前天" in msg:
#         return today - timedelta(days=2)
#     if "昨天" in msg:
#         return today - timedelta(days=1)
#     if "今天" in msg:
#         return today
#     # ISO date: 2026-04-20
#     m = re.search(r"(20\d{2})-(\d{1,2})-(\d{1,2})", msg)
#     if m:
#         try:
#             return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
#         except Exception:
#             pass
#     # Chinese month/day: 4月20日
#     m2 = re.search("(\d{1,2})月(\d{1,2})日", msg)
#     if m2:
#         try:
#             return date(today.year, int(m2.group(1)), int(m2.group(2)))
#         except Exception:
#             pass
#     # Weekday expressions: 本周三 / 下周一 / 周五
#     weekday_map = {
#         "一": 0,
#         "二": 1,
#         "三": 2,
#         "四": 3,
#         "五": 4,
#         "六": 5,
#         "日": 6,
#         "天": 6,
#     }
#     m3 = re.search("(本周|这周|下周)?(?:星期|周|礼拜)([一二三四五六日天])", msg)
#     if m3:
#         prefix = m3.group(1) or ""
#         target_wd = weekday_map.get(m3.group(2), today.weekday())
#         cur_wd = today.weekday()
#         delta = (target_wd - cur_wd) % 7
#         if prefix == "下周":
#             delta += 7
#         return today + timedelta(days=delta)
#     return today


# def _build_date_time_reply(text: str = "") -> str:
#     now = _localized_now()
#     today = now.date()
#     target = _resolve_date_target(text, today)
#     weekday = WEEKDAY_CN[target.weekday()]

#     msg = (text or "").strip()
#     ask_time = any(k in msg for k in ["几点", "时间", "time"])

#     if target == today and ask_time:
#         return f"今天是 {today.strftime('%Y-%m-%d')}（{weekday}），当前时间 {now.strftime('%H:%M:%S')}。"

#     if target == today:
#         label = "今天"
#     elif target == today + timedelta(days=1):
#         label = "明天"
#     elif target == today + timedelta(days=2):
#         label = "后天"
#     elif target == today - timedelta(days=1):
#         label = "昨天"
#     else:
#         label = "你问的日期"

#     return f"{label}是 {target.strftime('%Y-%m-%d')}（{weekday}）。"

def _validate_time_range(start_time: str, end_time: str) -> Optional[str]:
    if not start_time or not end_time:
        return "开始时间和结束时间不能为空。"

    try:
        st = _to_minutes(start_time)
        et = _to_minutes(end_time)
    except Exception:
        return "时间格式不正确，请使用 HH:MM。"

    if st >= et:
        return "开始时间必须早于结束时间。"

    return None


def _validate_schedule_window(schedule: Dict[str, Any], start_time: str, end_time: str) -> Optional[str]:
    open_time = str(schedule.get("open_time") or "")[:5]
    close_time = str(schedule.get("close_time") or "")[:5]
    if not open_time or not close_time:
        return None

    try:
        st = _to_minutes(start_time)
        et = _to_minutes(end_time)
        om = _to_minutes(open_time)
        cm = _to_minutes(close_time)
    except Exception:
        return "时间格式不正确。"

    if st < om or et > cm:
        return f"预约时间必须在实验室开放时间内（{open_time}-{close_time}）。"

    return None

def _free_slots_from_schedule(schedule: Dict[str, Any]) -> List[Tuple[int, int]]:
    open_time = schedule.get("open_time")
    close_time = schedule.get("close_time")
    if not open_time or not close_time:
        return []

    open_m = _to_minutes(str(open_time)[:5])
    close_m = _to_minutes(str(close_time)[:5])
    if open_m >= close_m:
        return []

    reservations = schedule.get("reservations") or []
    occupied: List[Tuple[int, int]] = []

    for r in reservations:
        try:
            s = _to_minutes(str(r["start_time"])[:5])
            e = _to_minutes(str(r["end_time"])[:5])
            if s < e:
                occupied.append((s, e))
        except Exception:
            continue

    occupied.sort()
    free: List[Tuple[int, int]] = []
    cur = open_m

    for s, e in occupied:
        if s > cur:
            free.append((cur, s))
        cur = max(cur, e)

    if cur < close_m:
        free.append((cur, close_m))

    return free


def _has_available_slot(schedule: Dict[str, Any], min_duration: int = 60) -> bool:
    for s, e in _free_slots_from_schedule(schedule):
        if e - s >= min_duration:
            return True
    return False

#=======================================================工具实现函数========================================
def _query_labs(date_text: str, campus: str, lab_type: str, participant_count: Optional[int] = None) -> List[Laboratory]:
    labs = Laboratory.query.filter_by(status="active").order_by(Laboratory.id.asc()).all()

    if campus:
        labs = [lab for lab in labs if lab.campus and campus in (lab.campus.campus_name or "")]

    if lab_type:
        labs = [
            lab for lab in labs
            if (lab.description and lab_type.lower() in lab.description.lower())
            or (lab.lab_name and lab_type.lower() in lab.lab_name.lower())
        ]

    if participant_count is not None:
        labs = [lab for lab in labs if (lab.capacity or 0) >= participant_count]

    if date_text:
        try:
            d = datetime.strptime(date_text, "%Y-%m-%d").date()
        except Exception:
            return []

        filtered: List[Laboratory] = []
        for lab in labs:
            schedule = get_lab_schedule(lab, d)
            if _has_available_slot(schedule, min_duration=60):
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

'''
这个推荐算法通过打分机制选择最优时段：
首先根据用户偏好（上午/下午/晚上）筛选出符合条件的候选时段，
然后计算每个候选时段的长度（分钟）作为基础分，
若时段符合用户偏好则额外加30分，
最后选择得分最高的时段作为推荐结果。
如果多个时段得分相同，则选择先遍历到的那个。
推荐时长会被限制在2小时以内，即使空闲段更长也只推荐前2小时。
整体逻辑是：有偏好时优先选符合偏好的最长时段，无偏好时直接选全天最长的空闲时段。
'''
def _recommend_time(date_text: str, lab_id: Optional[int], preference: str) -> Tuple[str, Optional[Dict[str, Any]]]:
    result = _query_schedule(date_text, lab_id)
    if not result.get("ok"):
        return result.get("message") or "无法查询排期。", None
    best = None
    best_score = -1

    def _preference_windows(pref_text: str) -> List[Tuple[int, int]]:
        pref = str(pref_text or "")
        if "上午" in pref:
            return [(8 * 60, 12 * 60)]
        if "下午" in pref:
            return [(12 * 60, 18 * 60)]
        if "晚上" in pref or "晚间" in pref:
            return [(18 * 60, 22 * 60)]
        return []

    preferred_windows = _preference_windows(preference)

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
            candidate_ranges: List[Tuple[int, int]] = []
            if preferred_windows:
                for ws, we in preferred_windows:
                    cs, ce = max(s, ws), min(e, we)
                    if ce - cs >= 60:
                        candidate_ranges.append((cs, ce))
            elif e - s >= 60:
                candidate_ranges.append((s, e))

            for cs, ce in candidate_ranges:
                dur = ce - cs
                score = dur
                if preferred_windows:
                    score += 30
                if score > best_score:
                    best_score = score
                    best = {"lab_id": lab.id, "lab_name": lab.lab_name, "start": cs, "end": min(cs + 120, ce)}
    if not best:
        return "当天没有合适的连续空闲时段。", None
    st = f"{best['start'] // 60:02d}:{best['start'] % 60:02d}"
    et = f"{best['end'] // 60:02d}:{best['end'] % 60:02d}"
    return f"我为你推荐: {date_text} {st}-{et}, 实验室 {best['lab_name']}。", {"date": date_text, "lab_id": best["lab_id"], "start_time": st, "end_time": et}


def _recommend_lab(
    date_text: str,
    campus: str,
    lab_type: str,
    participant_count: Optional[int],
    preference: str,
) -> Tuple[str, Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    labs = _query_labs(date_text, campus, lab_type, participant_count)
    if not labs:
        return "没有找到符合条件的可用实验室。", None, []

    pref_windows: List[Tuple[int, int]] = []
    pref = str(preference or "")
    if "上午" in pref:
        pref_windows = [(8 * 60, 12 * 60)]
    elif "下午" in pref:
        pref_windows = [(12 * 60, 18 * 60)]
    elif "晚上" in pref or "晚间" in pref:
        pref_windows = [(18 * 60, 22 * 60)]

    parsed_date: Optional[date] = None
    try:
        parsed_date = datetime.strptime(date_text, "%Y-%m-%d").date() if date_text else None
    except Exception:
        parsed_date = None

    ranked: List[Dict[str, Any]] = []
    for lab in labs:
        score = 0.0
        reasons: List[str] = []

        # 1) 容量贴合：满足人数前提下，越接近越优
        cap = _safe_int(getattr(lab, "capacity", None)) or 0
        if participant_count is not None and participant_count > 0:
            surplus = max(0, cap - participant_count)
            fit = max(0, 120 - surplus * 2)
            score += fit
            reasons.append(f"容量匹配度{int(fit)}")
        else:
            score += min(80, cap)

        # 2) 日期可用性：按最大连续空闲时长与总空闲时长打分
        max_free = 0
        total_free = 0
        pref_overlap = 0
        if parsed_date is not None:
            schedule = get_lab_schedule(lab, parsed_date)
            free_slots = _free_slots_from_schedule(schedule)
            for s, e in free_slots:
                dur = e - s
                if dur <= 0:
                    continue
                total_free += dur
                max_free = max(max_free, dur)
                for ws, we in pref_windows:
                    overlap = max(0, min(e, we) - max(s, ws))
                    pref_overlap += overlap
            score += max_free * 0.2 + total_free * 0.05
            if max_free > 0:
                reasons.append(f"最大连续空闲{max_free}分钟")

        # 3) 偏好时间命中
        if pref_windows:
            score += pref_overlap * 0.25
            if pref_overlap > 0:
                reasons.append(f"偏好时段重叠{pref_overlap}分钟")

        # 4) 校区/类型软加分（大部分已在筛选中）
        campus_name = getattr(lab.campus, "campus_name", "") if getattr(lab, "campus", None) else ""
        if campus and campus_name and campus in campus_name:
            score += 30
        if lab_type:
            desc = (getattr(lab, "description", "") or "") + " " + (getattr(lab, "lab_name", "") or "")
            if lab_type.lower() in desc.lower():
                score += 30

        ranked.append(
            {
                "lab_id": lab.id,
                "lab_name": lab.lab_name,
                "capacity": cap,
                "campus": campus_name,
                "score": round(score, 2),
                "reason": "，".join(reasons) if reasons else "综合评分最优",
            }
        )

    ranked.sort(key=lambda x: (-float(x.get("score") or 0), _safe_int(x.get("lab_id")) or 0))
    best = ranked[0] if ranked else None
    if not best:
        return "没有找到合适实验室。", None, []

    reply = f"推荐实验室：{best['lab_name']}（容量{best['capacity']}，校区{best['campus']}）。推荐理由：{best['reason']}。"
    return reply, best, ranked[:5]


def _extract_form_from_text(user, text: str, form: Dict[str, Any], session: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(form or {})
    relative_date = _resolve_relative_date(text)

    d = _detect_date(text)
    if d:
        merged["date"] = d

    st, et = _detect_time_range(text)
    if st:
        merged["start_time"] = st
    if et:
        merged["end_time"] = et
    if st and not et:
        duration = _detect_duration_minutes(text)
        if duration:
            merged["end_time"] = _add_minutes(st, duration)

    c = _detect_participant_count(text)
    if c is not None:
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

    pref = _detect_preference(text)
    if pref:
        merged["preference"] = pref

    lab_id = _detect_lab_id_or_choice(text, session)
    if lab_id is not None:
        merged["lab_id"] = lab_id

    if re.search(r"(这个时间|该时间|就这个时间|推荐的时间|这个时段)", text or ""):
        last_pick = session.get("last_recommended_time")
        if isinstance(last_pick, dict):
            for key in ["date", "start_time", "end_time"]:
                if last_pick.get(key):
                    merged[key] = last_pick.get(key)
            rid = _safe_int(last_pick.get("lab_id"))
            if rid is not None:
                merged["lab_id"] = rid

    merged = _llm_extract_form(text, merged)

    # 相对日期优先，防止 LLM 覆盖错
    if relative_date:
        merged["date"] = relative_date

    # 注意：这里不再默认 participant_count = 1
    return merged


def _normalize_chat_result(result: Any, trace_id: str = "") -> Dict[str, Any]:
    """
    标准化聊天结果为统一格式
    这是响应格式的统一出口，确保所有返回给前端的数据结构一致。
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
    # 动态从 AGENT_TOOL_SCHEMAS 生成，确保 description/returns 能传给 LLM
    # 避免维护两套工具定义导致不一致。
    tools: List[Dict[str, Any]] = []
    for tool_name, schema in AGENT_TOOL_SCHEMAS.items():
        tools.append(
            {
                "name": tool_name,
                "required": list(schema.get("required") or []),
                "optional": list(schema.get("optional") or []),
                "description": str(schema.get("description") or ""),
                "returns": str(schema.get("returns") or ""),
            }
        )
    
    # ==================== 3. 构建提示词 ====================
    # 将系统状态、工具定义、历史记录等信息组装成提示词
    # LLM 会根据这些信息做出决策
    prompt = f"""
你是实验室预约 Agent 规划器。每次只能做一步:
1) 选择一个工具执行，或
2) done=true 并给最终答复。

规则:
{_rules_context()}
- 如果信息不足以完成用户目标，优先继续推进：调用工具或明确追问缺失信息，不要空泛结束。
- 只有在“已满足用户请求”或“明确无法继续且已说明缺什么”时才 done=true。
- 用户目标若是创建预约，不要停在“推荐/查询”中间结果，应继续到可提交或明确缺参。

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
    # 将实验室对象列表转换为可直接展示给用户的文本结果
    if not labs:
        return "没有找到符合条件的实验室。"
    lines = []
    for i, lab in enumerate(labs, start=1):
        campus_name = getattr(lab.campus, "campus_name", "") if getattr(lab, "campus", None) else ""
        lines.append(f"{i}. ID={lab.id} | {lab.lab_name} | 容量={lab.capacity} | 校区={campus_name}")
    return "\n".join(lines)


def _schedule_result_to_text(result: Dict[str, Any]) -> str:
    # 将排期查询结果转换为用户可读的文本格式
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
    # 规范化前端页面路径，避免旧路径或别名路径导致跳转错误
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
    if factual:
        return factual

    if planner_reply:
        return planner_reply.strip()

    return "已处理完成。"


def _wants_create_flow(user_input: str) -> bool:
    """
    判断用户是否明确想“完成预约”，用于避免中间结果过早返回。
    """
    intent = _extract_intent(user_input or "")
    if intent == "create_reservation":
        return True
    msg = user_input or ""
    return any(k in msg for k in ["帮我预约", "创建预约", "直接预约", "下预约"])


def _wants_recommend_lab_flow(user_input: str) -> bool:
    intent = _extract_intent(user_input or "")
    if intent == "recommend_lab":
        return True
    msg = user_input or ""
    return any(k in msg for k in ["推荐实验室", "推荐一个实验室", "哪个实验室合适", "推荐个实验室"])


def _wants_recommend_time_flow(user_input: str) -> bool:
    intent = _extract_intent(user_input or "")
    if intent == "recommend_time":
        return True
    msg = user_input or ""
    return any(k in msg for k in ["推荐时间", "推荐时段", "什么时候能约", "哪个时间合适"])


def _has_relaxed_preference(text: str) -> bool:
    msg = text or ""
    return any(k in msg for k in ["随便", "都可以", "都行", "不限", "任意"])


def _recommend_lab_missing_fields(form: Dict[str, Any], user_input: str) -> List[str]:
    current = dict(form or {})
    missing: List[str] = []
    if not current.get("date"):
        missing.append("date")
    has_key_pref = any(
        [
            bool(current.get("campus")),
            current.get("participant_count") not in [None, "", 0],
            bool(current.get("type")),
            bool(current.get("preference")),
        ]
    )
    if not has_key_pref and not _has_relaxed_preference(user_input):
        missing.append("key_preference")
    return missing


def _recommend_time_missing_fields(form: Dict[str, Any], user_input: str) -> List[str]:
    current = dict(form or {})
    missing: List[str] = []
    if not current.get("date"):
        missing.append("date")
    has_time = bool(current.get("start_time") and current.get("end_time"))
    has_pref = bool(current.get("preference"))
    has_lab = current.get("lab_id") not in [None, ""]
    if not has_time and not has_pref and not has_lab and not _has_relaxed_preference(user_input):
        missing.append("lab_or_preference")
    return missing


def _needs_recommend_lab_clarification(form: Dict[str, Any], user_input: str) -> List[str]:
    if not _wants_recommend_lab_flow(user_input):
        return []
    return _recommend_lab_missing_fields(form, user_input)


def _needs_recommend_time_clarification(form: Dict[str, Any], user_input: str) -> List[str]:
    if not _wants_recommend_time_flow(user_input):
        return []
    return _recommend_time_missing_fields(form, user_input)


def _build_recommend_lab_clarification(missing: List[str]) -> str:
    if not missing:
        return ""
    parts: List[str] = []
    if "date" in missing:
        parts.append("哪一天")
    if "key_preference" in missing:
        parts.append("你更偏向哪个校区、几个人使用（也可以补充实验室类型或上午/下午偏好）")
    return "为了推荐得更准确，我先确认一下：" + "，".join(parts) + "。"


def _build_recommend_time_clarification(missing: List[str]) -> str:
    if not missing:
        return ""
    parts: List[str] = []
    if "date" in missing:
        parts.append("你想约哪一天")
    if "lab_or_preference" in missing:
        parts.append("有指定实验室吗（没有的话告诉我上午/下午/晚上偏好也行）")
    return "我先补两点信息再给你推荐时间：" + "，".join(parts) + "。"


def _needs_create_flow_clarification(form: Dict[str, Any], user_input: str) -> List[str]:
    """
    用户明确要创建预约时，先判断是否缺少“规划阶段”必须的信息。
    这里不等同于 create_reservation 的最终必填字段，而是用于先把需求问清楚。
    """
    if not _wants_create_flow(user_input):
        return []

    current = dict(form or {})
    missing: List[str] = []

    if not current.get("date"):
        missing.append("date")

    if not current.get("campus") and not current.get("lab_id"):
        missing.append("campus")

    has_time_range = bool(current.get("start_time") and current.get("end_time"))
    has_preference = bool(current.get("preference"))
    if not has_time_range and not has_preference:
        missing.append("time_range")
    elif has_preference and not has_time_range:
        missing.append("time_range_detail")

    if current.get("participant_count") in [None, "", 0]:
        missing.append("participant_count")

    if not str(current.get("purpose") or "").strip():
        missing.append("purpose")

    return missing


def _build_create_flow_clarification(missing: List[str], form: Dict[str, Any]) -> str:
    parts: List[str] = []

    if "date" in missing:
        parts.append("预约哪一天")
    if "campus" in missing:
        parts.append("想预约哪个校区")
    if "time_range" in missing:
        parts.append("具体几点到几点")
    if "time_range_detail" in missing:
        pref = str((form or {}).get("preference") or "").strip()
        if pref:
            parts.append(f"{pref}具体几点开始、几点结束")
        else:
            parts.append("具体几点到几点")
    if "participant_count" in missing:
        parts.append("几个人使用")
    if "purpose" in missing:
        parts.append("预约用途是什么")

    if not parts:
        return ""

    return "为了帮你把预约真正办下来，我还需要确认这些信息：" + "，".join(parts) + "。"


def _has_explicit_lab_reference_this_turn(text: str, session: Dict[str, Any]) -> bool:
    msg = (text or "").strip()
    if not msg:
        return False
    if _detect_lab_id_or_choice(msg, session) is not None:
        return True
    return bool(
        re.search(
            r"(实验室ID|lab_id|第\s*[0-9一二三四五]+\s*个|这个实验室|该实验室|就这个|就它|那个实验室|推荐的那个)",
            msg,
            re.IGNORECASE,
        )
    )


def _clear_followup_context(session: Dict[str, Any]) -> None:
    session["followup_context"] = None


def _set_followup_context(
    session: Dict[str, Any],
    source_tool: str,
    followup_cfg: Dict[str, Any],
    form: Dict[str, Any],
) -> None:
    cfg = dict(followup_cfg or {})
    preserve_fields = list(cfg.get("preserve_fields") or [])
    snapshot: Dict[str, Any] = {}
    for key in preserve_fields:
        value = (form or {}).get(key)
        if value not in [None, ""]:
            snapshot[key] = value

    now_ts = int(_localized_now().timestamp())
    cfg["source_tool"] = source_tool
    cfg["snapshot"] = snapshot
    cfg["created_at"] = now_ts
    cfg["expires_at"] = now_ts + FOLLOWUP_CONTEXT_TTL_SECONDS
    session["followup_context"] = cfg


def _message_hits_keywords(text: str, keywords: List[str]) -> bool:
    msg = (text or "").strip().lower()
    if not msg:
        return False
    for key in keywords or []:
        if str(key).strip().lower() in msg:
            return True
    return False


def _resolve_followup_expected_tool(ctx: Dict[str, Any], text: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    expected_tool = str(ctx.get("expected_tool") or "").strip()
    if expected_tool:
        return expected_tool, None

    options = ctx.get("options")
    if not isinstance(options, list):
        return None, None

    for opt in options:
        if not isinstance(opt, dict):
            continue
        triggers = opt.get("trigger")
        trigger_list: List[str] = []
        if isinstance(triggers, list):
            trigger_list = [str(x) for x in triggers]
        elif isinstance(triggers, str):
            trigger_list = [triggers]
        if trigger_list and _message_hits_keywords(text, trigger_list):
            tool = str(opt.get("tool") or "").strip()
            if tool:
                return tool, opt
    return None, None


def _continue_followup_context(user, text: str, session: Dict[str, Any], trace_id: str) -> Optional[Dict[str, Any]]:
    ctx = session.get("followup_context")
    if not isinstance(ctx, dict):
        return None

    now_ts = int(_localized_now().timestamp())
    expires_at = _safe_int(ctx.get("expires_at")) or 0
    if expires_at and now_ts > expires_at:
        _clear_followup_context(session)
        _debug_log(trace_id, "route", target="followup_expired")
        return None

    # 强意图切题时，清除续接上下文并进入常规路由
    intent = _extract_intent(text)
    if intent in {"cancel_reservation", "my_reservations", "update_reservation", "explain_rules", "navigate"}:
        _clear_followup_context(session)
        _debug_log(trace_id, "route", target="followup_cleared_by_strong_intent", intent=intent)
        return None

    form = dict(session.get("reservation_form") or {})
    form = _extract_form_from_text(user, text, form, session)
    session["reservation_form"] = form

    waiting_for = list(ctx.get("waiting_for") or [])
    missing_waiting = [k for k in waiting_for if (form or {}).get(k) in [None, ""]]
    if missing_waiting:
        return {
            "reply": "还差这些信息：" + "、".join(missing_waiting) + "。",
            "actions": [],
            "trace_id": trace_id,
        }

    required = ctx.get("required_response")
    if isinstance(required, list) and required:
        if not _message_hits_keywords(text, [str(x) for x in required]):
            # 常见确认词兜底，避免“好的/行”漏触发
            if not _message_hits_keywords(text, ["好", "可以", "行", "继续", "就这个", "确定"]):
                return None

    expected_tool, matched_option = _resolve_followup_expected_tool(ctx, text)
    if not expected_tool:
        return {
            "reply": "我可以继续帮你推进。你可以说“查排期”或“创建预约”。",
            "actions": [],
            "trace_id": trace_id,
        }

    params_seed: Dict[str, Any] = {}
    snapshot = ctx.get("snapshot") if isinstance(ctx.get("snapshot"), dict) else {}
    params_seed.update(snapshot)

    if isinstance(matched_option, dict):
        raw_params = matched_option.get("params")
        if isinstance(raw_params, dict):
            for key, value in raw_params.items():
                if value == "from_context":
                    if key in snapshot:
                        params_seed[key] = snapshot[key]
                else:
                    params_seed[key] = value

    params = _auto_fill_params(expected_tool, user, params_seed, form, text, session)
    result = _run_tool(expected_tool, params, user, session)

    if result.get("ok"):
        _clear_followup_context(session)
        reply = str(result.get("data") or "处理成功。")
        form = _sync_form_from_tool_result(form, expected_tool, result)
        session["reservation_form"] = form

        followup_text, followup_cfg = _build_followup_question(expected_tool, result, form)
        if isinstance(followup_cfg, dict):
            _set_followup_context(session, expected_tool, followup_cfg, form)
        if followup_text:
            reply = f"{reply}\n\n{followup_text}"

        return {
            "reply": reply,
            "actions": [{"label": "查看我的预约", "path": "/pages/my-reservations/my-reservations"}]
            if expected_tool in {"create_reservation", "update_reservation", "cancel_reservation"} and result.get("ok")
            else [],
            "trace_id": trace_id,
        }

    if result.get("error_code") == "missing_fields":
        missing = result.get("missing_fields") or []
        session["pending_action"] = {
            "tool": expected_tool,
            "missing": missing,
            "params": params,
        }
        _clear_followup_context(session)
        return {
            "reply": str(result.get("data") or _missing_fields_hint(expected_tool, missing)),
            "actions": [],
            "trace_id": trace_id,
        }

    _clear_followup_context(session)
    return {
        "reply": str(result.get("data") or "处理失败。"),
        "actions": [],
        "trace_id": trace_id,
    }


def _sync_form_from_tool_result(form: Dict[str, Any], tool: str, tool_result: Dict[str, Any]) -> Dict[str, Any]:
    # 根据工具执行结果回填表单字段，便于后续多轮对话继续使用
    if not isinstance(form, dict):
        return {}
    if not isinstance(tool_result, dict) or not tool_result.get("ok"):
        return form

    if tool == "recommend_lab":
        rid = _safe_int(tool_result.get("lab_id"))
        if rid is not None:
            form["lab_id"] = rid
        return form

    if tool == "recommend_time":
        pick = tool_result.get("pick")
        if isinstance(pick, dict):
            rid = _safe_int(pick.get("lab_id"))
            if rid is not None:
                form["lab_id"] = rid
            for key in ["date", "start_time", "end_time"]:
                value = pick.get(key)
                if value not in [None, ""]:
                    form[key] = value
        return form

    return form


def _auto_fill_params(tool: str, user, params: Dict[str, Any], form: Dict[str, Any], text: str, session: Dict[str, Any]) -> Dict[str, Any]:
    # 综合用户输入、当前表单和上下文信息，自动补全工具调用所需参数
    merged = _extract_form_from_text(user, text, form, session)
    pref = _detect_preference(text)
    if pref:
        merged["preference"] = pref
    raw = dict(params or {})
    for key in ["date", "participant_count", "start_time", "end_time", "purpose", "campus", "type", "lab_id", "preference"]:
        if not raw.get(key) and merged.get(key):
            raw[key] = merged[key]

    # get_lab_detail 仅在“本轮明确指定实验室”时继承/使用 lab_id；
    # 避免泛指请求（如“查看实验室详情”）误用历史上下文的 lab_id。
    if tool == "get_lab_detail" and not _has_explicit_lab_reference_this_turn(text, session):
        raw.pop("lab_id", None)

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


def _handle_query_labs(tool: str, params: Dict[str, Any], user, session: Dict[str, Any]) -> Dict[str, Any]:
    labs = _query_labs(
        params.get("date") or "",
        params.get("campus") or "",
        params.get("type") or "",
        _safe_int(params.get("participant_count")),
    )
    session["last_labs"] = [{"id": lab.id, "name": lab.lab_name} for lab in labs]
    session["last_choice_type"] = "lab_list"
    return _tool_result(tool, True, _labs_to_text(labs), extra={"labs_count": len(labs)})


def _handle_query_schedule(tool: str, params: Dict[str, Any], user, session: Dict[str, Any]) -> Dict[str, Any]:
    # 处理排期查询工具，将排期结果转换为统一返回格式
    result = _query_schedule(params.get("date"), _safe_int(params.get("lab_id")))
    return _tool_result(
        tool,
        bool(result.get("ok")),
        _schedule_result_to_text(result),
        error_code="query_failed" if not result.get("ok") else "",
        raw=result,
    )


def _handle_check_availability(tool: str, params: Dict[str, Any], user, session: Dict[str, Any]) -> Dict[str, Any]:
    lab_id = _safe_int(params.get("lab_id"))
    if lab_id is None:
        return _tool_result(tool, False, "缺少实验室ID", error_code="missing_fields")

    date_text = params.get("date")
    start_time = params.get("start_time")
    end_time = params.get("end_time")

    time_error = _validate_time_range(start_time, end_time)
    if time_error:
        return _tool_result(tool, False, time_error, error_code="invalid_time")

    try:
        target_date = datetime.strptime(date_text, "%Y-%m-%d").date()
    except Exception:
        return _tool_result(tool, False, "日期格式不正确，请使用 YYYY-MM-DD。", error_code="invalid_date")

    lab = Laboratory.query.get(lab_id)
    if not lab:
        return _tool_result(tool, False, "实验室不存在", error_code="not_found")

    schedule = get_lab_schedule(lab, target_date)

    window_error = _validate_schedule_window(schedule, start_time, end_time)
    if window_error:
        return _tool_result(tool, False, window_error, error_code="outside_open_time")

    st = _to_minutes(start_time)
    et = _to_minutes(end_time)

    rows = schedule.get("reservations") or []
    conflicts = []
    for r in rows:
        try:
            s = _to_minutes(str(r["start_time"])[:5])
            e = _to_minutes(str(r["end_time"])[:5])
        except Exception:
            continue
        if not (et <= s or st >= e):
            conflicts.append(f"{str(r['start_time'])[:5]}-{str(r['end_time'])[:5]}")

    if conflicts:
        return _tool_result(
            tool,
            False,
            f"该时间段不可预约，冲突时间段：{'；'.join(conflicts)}",
            error_code="time_conflict",
            raw={"conflicts": conflicts},
        )

    return _tool_result(
        tool,
        True,
        f"{date_text} {start_time}-{end_time} 可以预约。",
        raw={"available": True},
    )


def _handle_recommend_time(tool: str, params: Dict[str, Any], user, session: Dict[str, Any]) -> Dict[str, Any]:
    # 处理时间推荐工具，返回推荐时段及对应实验室信息
    reply, pick = _recommend_time(
        params.get("date"),
        _safe_int(params.get("lab_id")),
        str(params.get("preference") or ""),
    )
    if isinstance(pick, dict):
        session["last_recommended_time"] = {
            "lab_id": pick.get("lab_id"),
            "date": pick.get("date"),
            "start_time": pick.get("start_time"),
            "end_time": pick.get("end_time"),
        }
        session["last_choice_type"] = "time_recommendation"
    return _tool_result(
        tool,
        pick is not None,
        reply,
        error_code="no_slot" if pick is None else "",
        extra={"pick": pick},
    )


def _handle_recommend_lab(tool: str, params: Dict[str, Any], user, session: Dict[str, Any]) -> Dict[str, Any]:
    # 处理实验室推荐工具，使用评分算法返回最优推荐和候选列表
    reply, pick, ranked = _recommend_lab(
        params.get("date"),
        params.get("campus"),
        params.get("type"),
        _safe_int(params.get("participant_count")),
        str(params.get("preference") or ""),
    )
    if not pick:
        return _tool_result(tool, False, reply or "没有合适实验室", error_code="not_found")

    session["last_labs"] = [{"id": int(item["lab_id"]), "name": str(item["lab_name"])} for item in ranked]
    session["last_choice_type"] = "lab_list"
    return _tool_result(
        tool,
        True,
        reply,
        extra={"lab_id": pick.get("lab_id"), "pick": pick, "ranked_labs": ranked},
    )


def _handle_get_lab_detail(tool: str, params: Dict[str, Any], user, session: Dict[str, Any]) -> Dict[str, Any]:
    # 处理实验室详情查询工具，返回指定实验室的基本信息
    lab = Laboratory.query.get(_safe_int(params.get("lab_id")))
    if not lab:
        return _tool_result(tool, False, "实验室不存在", error_code="not_found")
    text = f"{lab.lab_name}，容量{lab.capacity}，位置{lab.location}"
    return _tool_result(tool, True, text, raw={"lab_id": lab.id})


def _handle_create_reservation(tool: str, params: Dict[str, Any], user, session: Dict[str, Any]) -> Dict[str, Any]:
    participant_count = _safe_int(params.get("participant_count"))
    payload = {
        "lab_id": _safe_int(params.get("lab_id")),
        "reservation_date": params.get("date"),
        "start_time": params.get("start_time"),
        "end_time": params.get("end_time"),
        "participant_count": participant_count,
        "purpose": params.get("purpose"),
    }
    if payload["participant_count"] is None:
        return _tool_result(
            tool,
            False,
            "还缺少这些信息: 参与人数。",
            error_code="missing_fields",
            error_message="missing required params",
            extra={"missing_fields": ["participant_count"]},
        )
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




def _handle_update_reservation(tool: str, params: Dict[str, Any], user, session: Dict[str, Any]) -> Dict[str, Any]:
    reservation_id = _safe_int(params.get("reservation_id"))
    reservation = Reservation.query.get(reservation_id)
    if not reservation:
        return _tool_result(tool, False, "预约不存在", error_code="not_found")

    if reservation.user_id != user.id:
        return _tool_result(tool, False, "你无权修改这条预约。", error_code="forbidden")

    new_date = params.get("date") or str(reservation.reservation_date)
    new_start = params.get("start_time") or str(reservation.start_time)[:5]
    new_end = params.get("end_time") or str(reservation.end_time)[:5]

    time_error = _validate_time_range(new_start, new_end)
    if time_error:
        return _tool_result(tool, False, time_error, error_code="invalid_time")

    try:
        target_date = datetime.strptime(new_date, "%Y-%m-%d").date()
    except Exception:
        return _tool_result(tool, False, "日期格式不正确，请使用 YYYY-MM-DD。", error_code="invalid_date")

    lab = reservation.lab
    if not lab:
        return _tool_result(tool, False, "预约关联的实验室不存在。", error_code="not_found")

    schedule = get_lab_schedule(lab, target_date)

    window_error = _validate_schedule_window(schedule, new_start, new_end)
    if window_error:
        return _tool_result(tool, False, window_error, error_code="outside_open_time")

    st = _to_minutes(new_start)
    et = _to_minutes(new_end)

    rows = schedule.get("reservations") or []
    for r in rows:
        rid = _safe_int(r.get("id"))
        if rid == reservation.id:
            continue
        try:
            s = _to_minutes(str(r["start_time"])[:5])
            e = _to_minutes(str(r["end_time"])[:5])
        except Exception:
            continue
        if not (et <= s or st >= e):
            return _tool_result(
                tool,
                False,
                f"修改失败：与 {str(r['start_time'])[:5]}-{str(r['end_time'])[:5]} 冲突。",
                error_code="time_conflict",
            )

    try:
        reservation.reservation_date = new_date
        reservation.start_time = new_start
        reservation.end_time = new_end
        db.session.commit()

        return _tool_result(
            tool,
            True,
            f"预约已更新：{lab.lab_name} {new_date} {new_start}-{new_end}",
            raw={
                "id": reservation.id,
                "lab_id": getattr(reservation, "lab_id", None),
                "reservation_date": new_date,
                "start_time": new_start,
                "end_time": new_end,
            },
        )
    except Exception:
        db.session.rollback()
        return _tool_result(tool, False, "预约更新失败，请稍后重试。", error_code="db_error")


def _handle_my_reservations(tool: str, params: Dict[str, Any], user, session: Dict[str, Any]) -> Dict[str, Any]:
    rows = (
        Reservation.query.filter_by(user_id=user.id)
        .filter(~Reservation.status.in_(["cancelled", "canceled"]))
        .order_by(Reservation.id.desc())
        .limit(8)
        .all()
    )
    if not rows:
        session["last_reservations"] = []
        session["last_choice_type"] = ""
        return _tool_result(tool, True, "暂无有效预约记录")

    session["last_reservations"] = [{"id": r.id} for r in rows]
    session["last_choice_type"] = "reservation_list"

    text = "\n".join([
        f"{idx}. 预约ID={r.id} | {r.lab.lab_name if r.lab else '-'} | {r.reservation_date} | "
        f"{str(r.start_time)[:5]}-{str(r.end_time)[:5]} | {getattr(r, 'status', '-')}"
        for idx, r in enumerate(rows, start=1)
    ])
    return _tool_result(tool, True, text)

def _handle_cancel_reservation(tool: str, params: Dict[str, Any], user, session: Dict[str, Any]) -> Dict[str, Any]:
    # 处理预约取消工具，调用取消服务撤销指定预约
    reservation = Reservation.query.get(_safe_int(params.get("reservation_id")))
    if not reservation:
        return _tool_result(tool, False, "预约不存在", error_code="not_found")
    try:
        updated = cancel_reservation(user, reservation)
        return _tool_result(tool, True, f"已取消预约 {updated.get('id')}", raw=updated)
    except AppError as exc:
        return _tool_result(tool, False, f"取消失败：{exc.message}")


def _handle_explain_rules(tool: str, params: Dict[str, Any], user, session: Dict[str, Any]) -> Dict[str, Any]:
    # 处理规则解释工具，返回当前实验室预约规则说明
    return _tool_result(tool, True, _rules_context())


def _handle_navigate(tool: str, params: Dict[str, Any], user, session: Dict[str, Any]) -> Dict[str, Any]:
    # 处理页面跳转工具，返回规范化后的目标页面路径
    return _tool_result(tool, True, _normalize_nav_path(params.get("path")))


def _handle_fill_form(tool: str, params: Dict[str, Any], user, session: Dict[str, Any]) -> Dict[str, Any]:
    # 处理表单填写工具，返回已填充的表单数据
    return _tool_result(tool, True, "已填写表单", raw={"form": params.get("form")})


def _handle_submit_form(tool: str, params: Dict[str, Any], user, session: Dict[str, Any]) -> Dict[str, Any]:
    # 处理表单提交工具，返回表单提交流程结果
    return _tool_result(tool, True, "表单已提交")


TOOL_HANDLERS = {
    "query_labs": _handle_query_labs,
    "query_schedule": _handle_query_schedule,
    "check_availability": _handle_check_availability,
    "recommend_time": _handle_recommend_time,
    "recommend_lab": _handle_recommend_lab,
    "get_lab_detail": _handle_get_lab_detail,
    "create_reservation": _handle_create_reservation,
    "update_reservation": _handle_update_reservation,
    "my_reservations": _handle_my_reservations,
    "cancel_reservation": _handle_cancel_reservation,
    "explain_rules": _handle_explain_rules,
    "navigate": _handle_navigate,
    "fill_form": _handle_fill_form,
    "submit_form": _handle_submit_form,
}


def _run_tool(tool: str, params: Dict[str, Any], user, session: Dict[str, Any]) -> Dict[str, Any]:
    trace_id = str(session.get("_debug_trace_id") or "")
    _debug_log(trace_id, "run_tool_enter", tool=tool, params=params)

    missing = _missing_required_tool_fields(tool, params)
    if missing:
        _debug_log(trace_id, "run_tool_missing_fields", tool=tool, missing=missing)
        session["pending_action"] = {
            "tool": tool,
            "missing": missing,
            "params": dict(params or {}),
        }
        return _tool_result(
            tool,
            False,
            _missing_fields_hint(tool, missing),
            error_code="missing_fields",
            error_message="missing required params",
            extra={"missing_fields": missing},
        )

    handler = TOOL_HANDLERS.get(tool)
    if not handler:
        _debug_log(trace_id, "run_tool_unknown", tool=tool)
        return _tool_result(tool, False, f"未知工具：{tool}", error_code="unknown_tool")

    return handler(tool, params, user, session)


def _fallback_rule_chat(user, text: str, session: Dict[str, Any]) -> Any:
    intent = _extract_intent(text)
    if intent == "cancel_flow" or _is_cancel_flow_message(text):
        _reset_form(session)
        return "好的，已退出当前预约流程。后续你可以继续让我查实验室、排期或帮你预约。"
    if intent == "query_labs":
        return _tool_call("query_labs", {}, "我来帮你查实验室。")
    if intent == "query_schedule":
        d = _detect_date(text)
        lid = _detect_lab_id_or_choice(text, session)
        params = {"date": d} if d else {}
        if lid is not None:
            params["lab_id"] = lid
        return _tool_call("query_schedule", params, "我来帮你查排期。")
    if intent == "create_reservation":
        return _tool_call("create_reservation", {}, "我来帮你创建预约。")
    if intent == "update_reservation":
        rid = _detect_reservation_id_or_choice(text, session)
        params = {"reservation_id": rid} if rid else {}
        d = _detect_date(text)
        if d:
            params["date"] = d
        st, et = _detect_time_range(text)
        if st:
            params["start_time"] = st
        if et:
            params["end_time"] = et
        return _tool_call("update_reservation", params, "我来帮你修改预约。")
    if intent == "my_reservations":
        return _tool_call("my_reservations", {}, "我帮你查询你的预约记录。")
    if intent == "cancel_reservation":
        rid = _detect_reservation_id_or_choice(text, session)
        params = {"reservation_id": rid} if rid else {}
        return _tool_call("cancel_reservation", params, "我来帮你取消该预约。")
    if intent == "recommend_lab":
        d = _detect_date(text)
        params: Dict[str, Any] = {}
        if d:
            params["date"] = d
        campus = _detect_campus(text)
        if campus:
            params["campus"] = campus
        c = _detect_participant_count(text)
        if c is not None:
            params["participant_count"] = c
        lab_type = _detect_type(text)
        if lab_type:
            params["type"] = lab_type
        pref = _detect_preference(text)
        if pref:
            params["preference"] = pref
        return _tool_call("recommend_lab", params, "我先帮你推荐实验室。")
    if intent == "recommend_time":
        d = _detect_date(text)
        params = {"date": d} if d else {}
        lid = _detect_lab_id_or_choice(text, session)
        if lid is not None:
            params["lab_id"] = lid
        pref = _detect_preference(text)
        if pref:
            params["preference"] = pref
        return _tool_call("recommend_time", params, "我帮你推荐时间。")
    if intent == "check_availability":
        d = _detect_date(text)
        st, et = _detect_time_range(text)
        lid = _detect_lab_id_or_choice(text, session)
        params = {}
        if lid is not None:
            params["lab_id"] = lid
        if d:
            params["date"] = d
        if st:
            params["start_time"] = st
        if et:
            params["end_time"] = et
        return _tool_call("check_availability", params, "我来帮你检查这个时段是否可预约。")
    if intent == "explain_rules":
        return _tool_call("explain_rules", {}, "我来说明一下预约规则。")
    if intent == "navigate":
        return _tool_call("navigate", {"path": "/pages/labs/labs"}, "我带你进入对应页面。")
    return _call_general_llm(user, text)


def _continue_pending_action(user, text: str, session: Dict[str, Any], trace_id: str) -> Optional[Dict[str, Any]]:
    pending = session.get("pending_action")
    if not isinstance(pending, dict):
        return None

    _clear_followup_context(session)

    tool = str(pending.get("tool") or "")
    if not tool:
        return None

    _debug_log(trace_id, "pending_action_continue", tool=tool, message=text)

    form = dict(session.get("reservation_form") or {})
    form = _extract_form_from_text(user, text, form, session)
    session["reservation_form"] = form

    # 创建预约在“规划阶段”的追问不直接执行工具；
    # 当高层信息补齐后，交回 agent_loop 继续推荐/检查/创建。
    if tool == "create_reservation":
        create_flow_missing = _needs_create_flow_clarification(form, text)
        if create_flow_missing:
            session["pending_action"] = {
                "tool": tool,
                "missing": create_flow_missing,
                "params": pending.get("params") or {},
            }
            _debug_log(trace_id, "pending_action_set", tool=tool, missing=create_flow_missing)
            return {
                "reply": _build_create_flow_clarification(create_flow_missing, form),
                "actions": [],
                "trace_id": trace_id,
            }

        session["pending_action"] = None
        _debug_log(trace_id, "pending_action_cleared", tool=tool)
        return None

    if tool == "recommend_lab":
        missing = _recommend_lab_missing_fields(form, text)
        if missing:
            session["pending_action"] = {
                "tool": tool,
                "missing": missing,
                "params": pending.get("params") or {},
            }
            _debug_log(trace_id, "pending_action_set", tool=tool, missing=missing)
            return {
                "reply": _build_recommend_lab_clarification(missing),
                "actions": [],
                "trace_id": trace_id,
            }

    if tool == "recommend_time":
        missing = _recommend_time_missing_fields(form, text)
        if missing:
            session["pending_action"] = {
                "tool": tool,
                "missing": missing,
                "params": pending.get("params") or {},
            }
            _debug_log(trace_id, "pending_action_set", tool=tool, missing=missing)
            return {
                "reply": _build_recommend_time_clarification(missing),
                "actions": [],
                "trace_id": trace_id,
            }

    params = _auto_fill_params(tool, user, pending.get("params") or {}, form, text, session)
    result = _run_tool(tool, params, user, session)

    if result.get("ok"):
        session["pending_action"] = None
        _debug_log(trace_id, "pending_action_cleared", tool=tool)
        return {
            "reply": str(result.get("data") or "处理成功。"),
            "actions": [{"label": "查看我的预约", "path": "/pages/my-reservations/my-reservations"}]
            if tool in {"create_reservation", "update_reservation", "cancel_reservation"}
            else [],
            "trace_id": trace_id,
        }

    if result.get("error_code") == "missing_fields":
        missing = result.get("missing_fields") or []
        session["pending_action"] = {
            "tool": tool,
            "missing": missing,
            "params": params,
        }
        _debug_log(trace_id, "pending_action_set", tool=tool, missing=missing)
        return {
            "reply": str(result.get("data") or "还需要补充信息。"),
            "actions": [],
            "trace_id": trace_id,
        }

    session["pending_action"] = None
    _debug_log(trace_id, "pending_action_cleared", tool=tool)
    return {
        "reply": str(result.get("data") or "处理失败。"),
        "actions": [],
        "trace_id": trace_id,
    }


def _should_fast_return_tool(tool: str, tool_result: Dict[str, Any]) -> bool:
    """
    哪些工具在成功执行后可以直接返回，不必再让 LLM 继续规划下一步
    """
    if not tool_result.get("ok"):
        return False

    fast_tools = {
        "query_labs",
        "query_schedule",
        "get_lab_detail",
        "my_reservations",
        "explain_rules",
        "recommend_lab",
        "recommend_time",
        "cancel_reservation",
        "navigate",
        "fill_form",
        "submit_form",
    }
    return tool in fast_tools

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
    Agent 主循环 - 改进版
    目标：
    1. LLM 决策下一步调用哪个工具
    2. 自动填充缺失参数
    3. 执行工具并处理结果
    4. 防止重复调用和 ABAB 死循环
    5. 查询类工具成功后快速返回，避免过度规划
    """

    # ==================== 1. 降级检查 ====================
    session["_debug_trace_id"] = trace_id
    _debug_log(trace_id, "agent_loop_start", user_input=user_input)

    if not Config.LLM_API_KEY:
        _debug_log(trace_id, "fallback_rule", reason="missing_llm_api_key")
        return _normalize_chat_result(
            _fallback_rule_chat(user, user_input, session),
            trace_id
        )

    # ==================== 2. 初始化循环状态 ====================
    context = user_input
    history: List[Dict[str, Any]] = []

    form = dict(session.get("reservation_form") or {})
    form = _extract_form_from_text(user, user_input, form, session)
    session["reservation_form"] = form
    _debug_log(trace_id, "form_initialized", form=form)

    create_flow_missing = _needs_create_flow_clarification(form, user_input)
    if create_flow_missing:
        reply = _build_create_flow_clarification(create_flow_missing, form)
        session["pending_action"] = {
            "tool": "create_reservation",
            "missing": create_flow_missing,
            "params": {},
        }
        _debug_log(trace_id, "pending_action_set", tool="create_reservation", missing=create_flow_missing)
        return {
            "reply": reply,
            "actions": [],
            "trace_id": trace_id,
        }

    recommend_lab_missing = _needs_recommend_lab_clarification(form, user_input)
    if recommend_lab_missing:
        reply = _build_recommend_lab_clarification(recommend_lab_missing)
        session["pending_action"] = {
            "tool": "recommend_lab",
            "missing": recommend_lab_missing,
            "params": {},
        }
        _debug_log(trace_id, "pending_action_set", tool="recommend_lab", missing=recommend_lab_missing)
        return {
            "reply": reply,
            "actions": [],
            "trace_id": trace_id,
        }

    recommend_time_missing = _needs_recommend_time_clarification(form, user_input)
    if recommend_time_missing:
        reply = _build_recommend_time_clarification(recommend_time_missing)
        session["pending_action"] = {
            "tool": "recommend_time",
            "missing": recommend_time_missing,
            "params": {},
        }
        _debug_log(trace_id, "pending_action_set", tool="recommend_time", missing=recommend_time_missing)
        return {
            "reply": reply,
            "actions": [],
            "trace_id": trace_id,
        }

    last_tool, same_tool_count = "", 0

    # ==================== 3. Agent 主循环 ====================
    for step in range(1, MAX_AGENT_STEPS + 1):

        # ----- 3.1 LLM 决策 -----
        decision = _llm_agent_decide(context, history, form) or {}
        tool = str(decision.get("tool") or "").strip()
        params = _normalize_params_shape(decision.get("params"))
        planner_reply = str(decision.get("reply") or "").strip()
        done = bool(decision.get("done", False))

        _debug_log(trace_id, "llm_decision", step=step, tool=tool, done=done, params=params)

        # ----- 3.2 终止条件 -----
        if done and not tool:
            final_reply = planner_reply or "处理完成。"
            _debug_log(trace_id, "done_return", step=step, reply_preview=final_reply[:120])
            return {
                "reply": final_reply,
                "actions": [],
                "trace_id": trace_id
            }

        if not tool:
            final_reply = planner_reply or "请补充更多信息。"
            _debug_log(trace_id, "done_return", step=step, reply_preview=final_reply[:120])
            return {
                "reply": final_reply,
                "actions": [],
                "trace_id": trace_id
            }

        # ----- 3.3 参数自动填充 -----
        params = _auto_fill_params(tool, user, params, form, user_input, session)
        _debug_log(trace_id, "params_filled", step=step, tool=tool, params=params)

        # 同步回表单
        for key in ["date", "participant_count", "start_time", "end_time",
                    "purpose", "campus", "type", "lab_id", "preference"]:
            if params.get(key) not in [None, ""]:
                form[key] = params.get(key)
        session["reservation_form"] = form

        # ----- 3.4 缺参时统一挂起 -----
        missing = _missing_required_tool_fields(tool, params)
        if missing:
            session["pending_action"] = {
                "tool": tool,
                "missing": missing,
                "params": dict(params or {}),
            }
            _debug_log(trace_id, "pending_action_set", tool=tool, missing=missing)
            return {
                "reply": _missing_fields_hint(tool, missing),
                "actions": [],
                "trace_id": trace_id,
            }

        # ----- 3.5 执行工具 -----
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

        form = _sync_form_from_tool_result(form, tool, tool_result)
        session["reservation_form"] = form
        _debug_log(trace_id, "form_synced_by_tool", step=step, tool=tool, form=form)

        # ----- 3.6 工具执行后仍缺参，也统一挂起 -----
        if tool_result.get("error_code") == "missing_fields":
            missing = tool_result.get("missing_fields") or []
            session["pending_action"] = {
                "tool": tool,
                "missing": missing,
                "params": dict(params or {}),
            }
            _debug_log(trace_id, "pending_action_set", tool=tool, missing=missing)
            return {
                "reply": str(tool_result.get("data") or _missing_fields_hint(tool, missing)),
                "actions": [],
                "trace_id": trace_id,
            }

        # ----- 3.7 记录执行历史 -----
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

        # ----- 3.7a 冲突后硬规则：优先推荐新时段 -----
        if tool == "check_availability" and not tool_result.get("ok") and tool_result.get("error_code") in {"conflict", "time_conflict"}:
            form["start_time"] = ""
            form["end_time"] = ""
            session["reservation_form"] = form

            rec_params: Dict[str, Any] = {
                "date": form.get("date"),
                "preference": form.get("preference") or ""
            }
            if form.get("lab_id"):
                rec_params["lab_id"] = form.get("lab_id")

            rec_params = _sanitize_tool_params("recommend_time", rec_params)
            _debug_log(trace_id, "run_tool_enter", tool="recommend_time(auto_after_conflict)", params=rec_params)

            rec_result = _run_tool("recommend_time", rec_params, user, session)
            _debug_log(
                trace_id,
                "tool_executed",
                step=step,
                tool="recommend_time(auto_after_conflict)",
                ok=bool(rec_result.get("ok")),
                error_code=rec_result.get("error_code"),
                data_preview=str(rec_result.get("data") or "")[:120],
            )

            if (
                not rec_result.get("ok")
                and rec_result.get("error_code") == "no_slot"
                and rec_params.get("lab_id") is not None
            ):
                rec_params.pop("lab_id", None)
                _debug_log(trace_id, "run_tool_enter", tool="recommend_time(auto_relax_lab)", params=rec_params)

                rec_result = _run_tool("recommend_time", rec_params, user, session)
                _debug_log(
                    trace_id,
                    "tool_executed",
                    step=step,
                    tool="recommend_time(auto_relax_lab)",
                    ok=bool(rec_result.get("ok")),
                    error_code=rec_result.get("error_code"),
                    data_preview=str(rec_result.get("data") or "")[:120],
                )

            if rec_result.get("ok"):
                form = _sync_form_from_tool_result(form, "recommend_time", rec_result)
                session["reservation_form"] = form
                _debug_log(trace_id, "form_synced_by_tool", step=step, tool="recommend_time(auto)", form=form)

                reply = str(rec_result.get("data") or "该时段冲突，已为你推荐其他可用时间。")
                _debug_log(trace_id, "done_return", step=step, reply_preview=reply[:120])
                return {
                    "reply": reply,
                    "actions": [],
                    "trace_id": trace_id,
                }

            reply = "你选择的时段已被占用，暂时没有找到合适替代时段。你可以告诉我新的时间范围（例如 14:00-16:00）。"
            _debug_log(trace_id, "done_return", step=step, reply_preview=reply[:120])
            return {
                "reply": reply,
                "actions": [],
                "trace_id": trace_id,
            }

        # ----- 3.7b 推荐时间失败时，若已限定实验室则自动放宽到全量实验室再试 -----
        if tool == "recommend_time" and not tool_result.get("ok") and tool_result.get("error_code") == "no_slot":
            if params.get("lab_id") is not None:
                relaxed_params = dict(params)
                relaxed_params.pop("lab_id", None)
                relaxed_params = _sanitize_tool_params("recommend_time", relaxed_params)
                _debug_log(trace_id, "run_tool_enter", tool="recommend_time(auto_relax_lab)", params=relaxed_params)

                relaxed_result = _run_tool("recommend_time", relaxed_params, user, session)
                _debug_log(
                    trace_id,
                    "tool_executed",
                    step=step,
                    tool="recommend_time(auto_relax_lab)",
                    ok=bool(relaxed_result.get("ok")),
                    error_code=relaxed_result.get("error_code"),
                    data_preview=str(relaxed_result.get("data") or "")[:120],
                )

                if relaxed_result.get("ok"):
                    form = _sync_form_from_tool_result(form, "recommend_time", relaxed_result)
                    session["reservation_form"] = form
                    _debug_log(trace_id, "form_synced_by_tool", step=step, tool="recommend_time(auto_relax_lab)", form=form)
                    tool_result = relaxed_result
                    tool = "recommend_time"

        # ----- 3.8 重复调用检测 -----
        same_tool_count = same_tool_count + 1 if tool == last_tool else 1
        last_tool = tool

        if same_tool_count > MAX_TOOL_REPEAT_STEPS:
            reply = "同一步骤重复尝试过多次。请补充更具体信息后我再继续。"
            _debug_log(trace_id, "done_return", step=step, reply_preview=reply[:120])
            return {
                "reply": reply,
                "actions": [],
                "trace_id": trace_id
            }

        if _is_abab_loop(history):
            reply = "我检测到策略在重复尝试（如查冲突/换实验室来回循环）。请告诉我你更倾向的新时间范围，我马上按新范围推荐。"
            _debug_log(trace_id, "done_return", step=step, reply_preview=reply[:120])
            return {
                "reply": reply,
                "actions": [],
                "trace_id": trace_id,
            }

        # ==================== 4. 查询/动作类工具快速返回 ====================

        # 4.1 导航类
        if tool == "navigate" and tool_result.get("ok"):
            reply = planner_reply or "我带你进入对应页面。"
            _debug_log(trace_id, "done_return", step=step, reply_preview=reply[:120])
            return {
                "reply": reply,
                "actions": [{"label": "前往页面", "path": str(tool_result.get("data") or "/pages/agent/agent")}],
                "trace_id": trace_id
            }

        # 4.2 我的预约 / 取消预约
        if tool in {"my_reservations", "cancel_reservation"}:
            _clear_followup_context(session)
            reply = _tool_reply_prefer_facts(tool, tool_result, planner_reply, params)
            _debug_log(trace_id, "done_return", step=step, reply_preview=reply[:120])
            return {
                "reply": reply,
                "actions": [{"label": "查看我的预约", "path": "/pages/my-reservations/my-reservations"}],
                "trace_id": trace_id
            }

        # 4.3 创建 / 修改预约
        if tool in {"create_reservation", "update_reservation"}:
            _clear_followup_context(session)
            reply = _tool_reply_prefer_facts(tool, tool_result, planner_reply, params)
            _debug_log(trace_id, "done_return", step=step, reply_preview=reply[:120])
            return {
                "reply": reply,
                "actions": [{"label": "查看我的预约", "path": "/pages/my-reservations/my-reservations"}] if tool_result.get("ok") else [],
                "trace_id": trace_id
            }

        # 4.4 其他查询类成功后直接返回
        if _should_fast_return_tool(tool, tool_result):
            # 用户目标是“完成预约”时，不在中间查询/推荐结果提前结束，继续规划到可提交或明确缺参。
            if _wants_create_flow(user_input) and tool in {
                "query_labs",
                "query_schedule",
                "recommend_lab",
                "recommend_time",
                "get_lab_detail",
                "check_availability",
            }:
                _debug_log(trace_id, "route", target="continue_planning", reason="create_flow_not_finished", step=step, tool=tool)
            else:
                reply = _tool_reply_prefer_facts(tool, tool_result, planner_reply, params)
                followup_text, followup_cfg = _build_followup_question(tool, tool_result, form)
                if isinstance(followup_cfg, dict):
                    _set_followup_context(session, tool, followup_cfg, form)
                else:
                    _clear_followup_context(session)
                if followup_text:
                    reply = f"{reply}\n\n{followup_text}"
                _debug_log(trace_id, "done_return", step=step, reply_preview=reply[:120])
                return {
                    "reply": reply,
                    "actions": [],
                    "trace_id": trace_id
                }

        # 4.5 LLM 本轮已标记完成
        if done:
            if _wants_create_flow(user_input) and tool in {
                "query_labs",
                "query_schedule",
                "recommend_lab",
                "recommend_time",
                "get_lab_detail",
                "check_availability",
            }:
                _debug_log(trace_id, "route", target="continue_planning", reason="done_but_create_flow_not_finished", step=step, tool=tool)
            else:
                final_reply = _tool_reply_prefer_facts(tool, tool_result, planner_reply, params)
                followup_text, followup_cfg = _build_followup_question(tool, tool_result, form)
                if isinstance(followup_cfg, dict):
                    _set_followup_context(session, tool, followup_cfg, form)
                else:
                    _clear_followup_context(session)
                if followup_text:
                    final_reply = f"{final_reply}\n\n{followup_text}"
                _debug_log(trace_id, "done_return", step=step, reply_preview=final_reply[:120])
                return {
                    "reply": final_reply,
                    "actions": [],
                    "trace_id": trace_id
                }

        # 4.6 不可恢复错误直接返回
        if not tool_result.get("ok") and tool_result.get("error_code") in {
            "invalid_params",
            "not_found",
            "business_rule"
        }:
            reply = str(tool_result.get("data") or "处理失败。")
            _debug_log(trace_id, "done_return", step=step, reply_preview=reply[:120])
            return {
                "reply": reply,
                "actions": [],
                "trace_id": trace_id
            }

        # ==================== 5. 更新上下文，继续下一轮 ====================
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

    # ==================== 6. 超过最大步数，降级 ====================
    _debug_log(trace_id, "fallback_rule", reason="max_steps_exceeded")
    return _normalize_chat_result(
        _fallback_rule_chat(user, user_input, session),
        trace_id
    )

def chat(user, message):
    print("=========================================================下一轮对话============================================================")
    """
    对话主入口函数 - 处理用户消息并返回 Agent 响应
    这是整个 Agent 系统的统一入口，负责：
    1. 消息预处理和验证
    2. 用户会话管理
    3. 意图路由（实验室相关 / 通用问题）
    4. 错误处理和降级方案
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
        if _is_cancel_flow_message(text) and isinstance(session.get("pending_action"), dict):
            _debug_log(trace_id, "route", target="cancel_flow")
            _reset_form(session)           # 清空预约表单
            _save_session(user_id, session) # 保存会话状态
            return _normalize_chat_result(
                "好的，已退出当前预约流程。后续你可以继续让我查实验室、排期或帮你预约。",
                trace_id
            )

        pending_result = _continue_pending_action(user, text, session, trace_id)
        if pending_result is not None:
            _save_session(user_id, session)
            return _normalize_chat_result(pending_result, trace_id)

        followup_result = _continue_followup_context(user, text, session, trace_id)
        if followup_result is not None:
            _debug_log(trace_id, "route", target="followup_context")
            session["last_domain"] = "lab"
            _save_session(user_id, session)
            return _normalize_chat_result(followup_result, trace_id)

        # ----- 4.2 实验室相关问题 vs 通用问题 -----
        # 判断用户问题是否与实验室预约相关
        # 相关关键词：实验室、预约、排期、空闲、lab、schedule等
        lab_related = _is_lab_related(text)
        lab_followup = _is_lab_followup(text, session)
        if lab_related or lab_followup:
            _debug_log(trace_id, "route", target="agent_loop", lab_related=lab_related, lab_followup=lab_followup)
            session["last_domain"] = "lab"
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
        session["last_domain"] = "general"
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

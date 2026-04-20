import json
import re
from typing import Any, Dict, List, Optional

# 防循环检测，避免对话陷入重复模式
def is_abab_loop(history: List[Dict[str, Any]]) -> bool:
    if len(history) < 4:
        return False
    tools = [str(x.get("tool") or "") for x in history[-4:]]
    return tools[0] == tools[2] and tools[1] == tools[3] and tools[0] != tools[1]

# 记录要调用哪个工具和参数
def tool_call(tool: str, params: Dict[str, Any], reply: str) -> Dict[str, Any]:
    return {"type": "tool_call", "tool": tool, "params": params, "reply": reply}

# 记录工具执行结果（成功/失败/错误码）
def tool_result(
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

# 参数格式统一为字典
def normalize_params_shape(params: Any) -> Dict[str, Any]:
    return dict(params) if isinstance(params, dict) else {}

# 安全的整数转换，不抛异常
def safe_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except Exception:
        return None

# 安全的 JSON 解析，支持多种格式
def safe_json_loads(text: str) -> Optional[Dict[str, Any]]:
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

# 关键词匹配检查
def contains_any(msg: str, keywords: List[str]) -> bool:
    return any(k in msg for k in keywords)

# 时间字符串转分钟数（便于比较时间）
def to_minutes(hhmm: str) -> int:
    h, m = [int(i) for i in hhmm.split(":")]
    return h * 60 + m


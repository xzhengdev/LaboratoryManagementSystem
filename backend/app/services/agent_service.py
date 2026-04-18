"""
AI助手服务模块 (agent_service.py)
功能：处理用户对话，支持规则匹配和 LLM 两种模式
      提供实验室查询、预约管理、统计信息等智能回复
"""

import json                     # JSON 序列化/反序列化（用于 API 请求）
import re                       # 正则表达式（用于日期识别）
from datetime import date, timedelta  # 日期处理

import requests                 # HTTP 请求库（用于调用 LLM API）

from app.config import Config   # 应用配置（LLM API 密钥、模型等）
from app.models import Laboratory, Reservation  # 数据模型
from app.services.reservation_service import get_lab_schedule  # 排期服务


# ==================== 日期识别 ====================
def detect_date(message):
    """
    从用户消息中识别日期
    支持的日期表达：
        - "今天"      → 当天日期
        - "明天"      → 明天日期
        - "2024-01-15" → 指定日期
    参数：
        message - 用户输入的消息文本
    返回：
        date 对象（识别失败时返回今天）
    """
    # 规则1：今天
    if "今天" in message:
        return date.today()
    
    # 规则2：明天
    if "明天" in message:
        return date.today() + timedelta(days=1)

    # 规则3：匹配 YYYY-MM-DD 格式
    matched = re.search(r"(20\d{2}-\d{2}-\d{2})", message)
    if matched:
        # 解析年月日
        year, month, day = [int(part) for part in matched.group(1).split("-")]
        return date(year, month, day)
    # 默认：返回今天
    return date.today()


# ==================== 帮助信息 ====================
def build_help_reply():
    """
    构建帮助回复（当无法识别用户意图时）
    返回：
        包含回复文本和操作建议的字典
    """
    return {
        "reply": (
            "我是实验室预约助手，可以帮你查询预约、空闲实验室、实验室排期和统计信息。\n"
            "你可以试试：\n"
            "1. 帮我看看今天有哪些实验室还能预约\n"
            "2. 查看我的预约\n"
        )
    }


# ==================== 我的预约查询 ====================
def summarize_reservations(user):
    """
    查询当前用户的预约记录并生成摘要
    参数：
        user - 当前登录用户对象
    
    返回：
        包含最近5条预约记录的回复
    """
    # 查询用户最近5条预约（按日期倒序、时间倒序）
    items = (
        Reservation.query.filter_by(user_id=user.id)
        .order_by(Reservation.reservation_date.desc(), Reservation.start_time.desc())
        .limit(5)
        .all()
    )
    
    # 无预约记录
    if not items:
        return {
            "reply": "你当前还没有预约记录，可以先去实验室列表挑选可用时段。",
            "actions": [{"label": "去预约", "path": "/pages/labs/index"}],
        }

    # 构建预约摘要列表
    lines = [
        f"{item.lab.lab_name} | {item.reservation_date.isoformat()} "
        f"{item.start_time.strftime('%H:%M')}-{item.end_time.strftime('%H:%M')} | {item.status}"
        for item in items
    ]
    
    return {
        "reply": "最近的预约如下：\n" + "\n".join(lines),
        "actions": [{"label": "查看详情", "path": "/pages/my-reservations/index"}],
    }


# ==================== 可用实验室查询 ====================
def summarize_available_labs(target_date):
    """
    查询指定日期可用的实验室列表
    参数：
        target_date - 目标日期
    返回：
        包含实验室摘要信息的回复
    """
    # 查询所有活跃状态的实验室
    labs = (
        Laboratory.query.filter_by(status="active")
        .order_by(Laboratory.campus_id.asc())
        .all()
    )
    
    if not labs:
        return {"reply": "当前没有可用实验室。", "actions": []}

    # 构建实验室摘要（最多8条）
    lines = []
    for lab in labs[:8]:
        schedule = get_lab_schedule(lab, target_date)
        lines.append(
            f"{lab.lab_name}（{lab.campus.campus_name}）开放 "
            f"{schedule['open_time']}-{schedule['close_time']}，"
            f"已有 {len(schedule['reservations'])} 段预约"
        )

    return {
        "reply": f"{target_date.isoformat()} 可关注的实验室如下：\n" + "\n".join(lines),
        "actions": [{"label": "查看实验室", "path": "/pages/labs/index"}],
    }


# ==================== 单个实验室排期查询 ====================
def summarize_single_lab(message, target_date):
    """
    查询指定实验室在某天的排期
    
    参数：
        message     - 用户消息（用于匹配实验室名称）
        target_date - 目标日期
    
    返回：
        包含实验室排期的回复，如果没有匹配则返回 None
    """
    # 获取所有活跃实验室
    labs = Laboratory.query.filter_by(status="active").all()
    
    # 匹配实验室名称（消息中包含实验室名称）
    matched_lab = None
    for lab in labs:
        if lab.lab_name in message:
            matched_lab = lab
            break

    # 未匹配到实验室
    if not matched_lab:
        return None

    # 获取实验室排期
    schedule = get_lab_schedule(matched_lab, target_date)
    reservations = schedule["reservations"]
    
    # 构建回复
    if not reservations:
        reply = (
            f"{matched_lab.lab_name} 在 {target_date.isoformat()} 暂无预约，"
            f"开放时间为 {schedule['open_time']}-{schedule['close_time']}。"
        )
    else:
        lines = [
            f"{item['start_time'][:5]}-{item['end_time'][:5]} | "
            f"{item['status']} | {item['purpose']}"
            for item in reservations
        ]
        reply = (
            f"{matched_lab.lab_name} 在 {target_date.isoformat()} 的排期如下：\n"
            + "\n".join(lines)
        )

    return {
        "reply": reply,
        "actions": [
            {
                "label": "查看排期",
                "path": (
                    f"/pages/schedule/index?labId={matched_lab.id}"
                    f"&date={target_date.isoformat()}"
                ),
            }
        ],
    }


# ==================== LLM 调用（OpenAI/DeepSeek 兼容）====================
def call_llm_compatible(user, message):
    """
    调用 LLM API（兼容 OpenAI 和 DeepSeek）
    参数：
        user    - 当前用户对象（用于提供角色信息）
        message - 用户消息
    返回：
        LLM 生成的回复
    异常：
        请求失败时抛出异常
    """
    # 构建请求头
    headers = {
        "Authorization": f"Bearer {Config.LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    
    # 构建系统提示词（包含用户角色信息）
    system_prompt = (
        "你是中央民族大学实验室预约系统内的智能助手。"
        "请用中文、简洁、可执行的方式回答。"
        f"当前用户角色是 {user.role}，姓名是 {user.real_name}。"
    )
    
    # 构建请求体
    payload = {
        "model": Config.AGENT_MODEL,  # 使用的模型
        "messages": [
            {"role": "system", "content": system_prompt},  # 系统提示
            {"role": "user", "content": message},          # 用户消息
        ],
        "temperature": 0.4,  # 控制回复的随机性（0-1，越低越确定）
    }
    
    # 发送请求
    response = requests.post(
        Config.LLM_BASE_URL,
        headers=headers,
        data=json.dumps(payload),
        timeout=20,  # 20秒超时
    )
    
    # 检查响应状态
    response.raise_for_status()
    
    # 解析响应
    data = response.json()
    content = data["choices"][0]["message"]["content"]
    
    return {"reply": content, "actions": []}


# ==================== 主入口：对话处理 ====================
def chat(user, message):
    """
    AI 对话主函数
    
    处理流程：
        1. 如果配置了 LLM 且可用，优先使用 LLM 模式
        2. LLM 失败或未配置时，降级到规则引擎
        3. 规则引擎按优先级匹配意图
    
    参数：
        user    - 当前登录用户对象
        message - 用户输入的消息
    
    返回：
        包含 reply（回复文本）和 actions（建议操作）的字典
    """
    # ===== 模式1：LLM 模式 =====
    # 如果配置了 LLM 提供商且有 API 密钥，尝试调用 LLM
    if Config.AGENT_PROVIDER in {"openai", "deepseek", "llm"} and Config.LLM_API_KEY:
        try:
            return call_llm_compatible(user, message)
        except Exception:
            # LLM 调用失败，降级到规则引擎
            pass

    # ===== 模式2：规则引擎模式 =====
    
    # 识别日期（用于实验室查询）
    target_date = detect_date(message)

    # ----- 意图1：我的预约 -----
    if "我的预约" in message or "查看预约" in message:
        return summarize_reservations(user)

    # ----- 意图2：统计信息 -----
    if "统计" in message:
        total = Reservation.query.count()
        approved = Reservation.query.filter_by(status="approved").count()
        pending = Reservation.query.filter_by(status="pending").count()
        return {
            "reply": (
                f"当前共有 {total} 条预约，其中已通过 {approved} 条，"
                f"待审批 {pending} 条。"
            ),
            "actions": [{"label": "去统计页", "path": "/pages/statistics/index"}],
        }

    # ----- 意图3：单个实验室排期 -----
    single_lab_reply = summarize_single_lab(message, target_date)
    if single_lab_reply:
        return single_lab_reply

    # ----- 意图4：可用实验室查询 -----
    if "可预约" in message or "空闲" in message or "实验室" in message:
        return summarize_available_labs(target_date)

    # ----- 默认：帮助信息 -----
    return build_help_reply()
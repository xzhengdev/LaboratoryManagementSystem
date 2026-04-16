import json
import re
from datetime import date, timedelta

import requests

from app.config import Config
from app.models import Laboratory, Reservation
from app.services.reservation_service import get_lab_schedule


def detect_date(message):
    if "今天" in message:
        return date.today()
    if "明天" in message:
        return date.today() + timedelta(days=1)

    matched = re.search(r"(20\d{2}-\d{2}-\d{2})", message)
    if matched:
        year, month, day = [int(part) for part in matched.group(1).split("-")]
        return date(year, month, day)

    return date.today()


def build_help_reply():
    return {
        "reply": (
            "我是实验室预约助手，可以帮你查询预约、空闲实验室、实验室排期和统计信息。\n"
            "你可以试试：\n"
            "1. 帮我看看今天有哪些实验室还能预约\n"
            "2. 查看我的预约\n"
            "3. A101 实验室明天的排期\n"
            "4. 给我看统计概览"
        ),
        "actions": [
            {"label": "我的预约", "path": "/pages/my-reservations/index"},
            {"label": "实验室列表", "path": "/pages/labs/index"},
            {"label": "统计页", "path": "/pages/statistics/index"},
        ],
    }


def summarize_reservations(user):
    items = (
        Reservation.query.filter_by(user_id=user.id)
        .order_by(Reservation.reservation_date.desc(), Reservation.start_time.desc())
        .limit(5)
        .all()
    )
    if not items:
        return {
            "reply": "你当前还没有预约记录，可以先去实验室列表挑选可用时段。",
            "actions": [{"label": "去预约", "path": "/pages/labs/index"}],
        }

    lines = [
        f"{item.lab.lab_name} | {item.reservation_date.isoformat()} "
        f"{item.start_time.strftime('%H:%M')}-{item.end_time.strftime('%H:%M')} | {item.status}"
        for item in items
    ]
    return {
        "reply": "最近的预约如下：\n" + "\n".join(lines),
        "actions": [{"label": "查看详情", "path": "/pages/my-reservations/index"}],
    }


def summarize_available_labs(target_date):
    labs = (
        Laboratory.query.filter_by(status="active")
        .order_by(Laboratory.campus_id.asc())
        .all()
    )
    if not labs:
        return {"reply": "当前没有可用实验室。", "actions": []}

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


def summarize_single_lab(message, target_date):
    labs = Laboratory.query.filter_by(status="active").all()
    matched_lab = None
    for lab in labs:
        if lab.lab_name in message:
            matched_lab = lab
            break

    if not matched_lab:
        return None

    schedule = get_lab_schedule(matched_lab, target_date)
    reservations = schedule["reservations"]
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


def call_llm_compatible(user, message):
    headers = {
        "Authorization": f"Bearer {Config.LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    system_prompt = (
        "你是实验室预约系统内的智能助手。"
        "请用中文、简洁、可执行的方式回答。"
        f"当前用户角色是 {user.role}，姓名是 {user.real_name}。"
    )
    payload = {
        "model": Config.AGENT_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message},
        ],
        "temperature": 0.4,
    }
    response = requests.post(
        Config.LLM_BASE_URL,
        headers=headers,
        data=json.dumps(payload),
        timeout=20,
    )
    response.raise_for_status()
    data = response.json()
    content = data["choices"][0]["message"]["content"]
    return {"reply": content, "actions": []}


def chat(user, message):
    if Config.AGENT_PROVIDER in {"openai", "deepseek", "llm"} and Config.LLM_API_KEY:
        try:
            return call_llm_compatible(user, message)
        except Exception:
            pass

    target_date = detect_date(message)

    if "我的预约" in message or "查看预约" in message:
        return summarize_reservations(user)

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

    single_lab_reply = summarize_single_lab(message, target_date)
    if single_lab_reply:
        return single_lab_reply

    if "可预约" in message or "空闲" in message or "实验室" in message:
        return summarize_available_labs(target_date)

    return build_help_reply()

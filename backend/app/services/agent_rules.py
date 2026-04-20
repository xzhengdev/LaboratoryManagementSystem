from typing import Any, Dict, List, Optional, Tuple


def missing_fields_hint(tool: str, missing: List[str]) -> str:
    common_label_map = {
        "lab_id": "实验室ID",
        "date": "预约日期(YYYY-MM-DD)",
        "start_time": "开始时间(HH:MM)",
        "end_time": "结束时间(HH:MM)",
        "participant_count": "参与人数",
        "purpose": "用途说明",
        "reservation_id": "预约ID",
        "path": "页面路径",
        "form": "表单数据",
    }

    if tool in {"create_reservation", "update_reservation"}:
        labels = [common_label_map.get(x, x) for x in missing]
        return "缺少信息: " + "、".join(labels) + "。"

    if tool == "recommend_lab":
        return "为了更准确推荐实验室，请告诉我日期，并尽量补充校区、人数和实验室类型偏好。"

    if tool == "recommend_time":
        return "请先告诉我日期；如果有指定实验室或上午/下午偏好也可以一起说。"

    if tool == "query_schedule":
        return "请先告诉我日期"

    if tool == "cancel_reservation":
        return "请告诉我要取消的预约ID，例如：取消预约ID 23。"

    labels = [common_label_map.get(x, x) for x in missing]
    return "参数不完整，请补充这些信息：" + "、".join(labels) + "。"


def build_followup_question(
    tool: str,
    tool_result: Dict[str, Any],
    form: Dict[str, Any],
) -> Tuple[str, Optional[Dict[str, Any]]]:
    """
    返回: (追问文本, 续接动作配置)
    """
    if not tool_result.get("ok"):
        return "", None

    if tool == "query_labs":
        return (
            "要不要我继续按日期给你筛选可预约实验室？"
            "你可以这样回复：\n"
            "• “好，帮我筛选明天的”\n"
            "• “继续，查一下后天下午的”\n"
            "• “要，日期2026-04-25”",
            {
                "expected_tool": "query_labs",
                "required_response": ["要", "好", "可以", "继续", "筛选"],
                "expected_fields": ["date"],  # 期望用户提供的字段
                "context_preserve": True,
            },
        )

    if tool == "recommend_lab":
        return (
            "要不要我基于这个实验室继续推荐具体可用时间段？",
            {
                "expected_tool": "recommend_time",
                "required_response": ["要", "好", "可以", "继续", "推荐时间", "时段"],
                "context_preserve": True,
                "preserve_fields": ["lab_id", "date", "preference"],
            },
        )

    if tool == "recommend_time":
        return (
            "可以直接回复“创建预约”让我帮你预定这个时间段。",
            {
                "expected_tool": "create_reservation",
                "required_response": ["创建预约", "好的", "预约", "就这个", "确定", "提交"],
                "context_preserve": True,
                "preserve_fields": ["date", "start_time", "end_time", "lab_id", "participant_count", "purpose"],
                "auto_fill": True,
            },
        )

    if tool == "get_lab_detail":
        return (
            "要不要我再查这个实验室明天的排期，或直接帮你预约一个时间段？",
            {
                "expected_tool": None,
                "options": [
                    {"trigger": ["查排期", "排期", "时间安排"], "tool": "query_schedule"},
                    {"trigger": ["预约", "创建预约", "预定"], "tool": "create_reservation"},
                ],
                "context_preserve": True,
                "preserve_fields": ["lab_id"],
            },
        )

    if tool == "check_availability":
        purpose = str((form or {}).get("purpose") or "").strip()
        if purpose:
            return (
                "这个时段可用。回复“创建预约”我就直接提交。",
                {
                    "expected_tool": "create_reservation",
                    "required_response": ["创建预约", "好的", "预约", "提交"],
                    "context_preserve": True,
                    "preserve_fields": ["date", "start_time", "end_time", "lab_id", "participant_count", "purpose"],
                    "auto_fill": True,
                },
            )
        return (
            "这个时段可用。还差预约用途（purpose），补充后我就能直接创建预约。",
            {
                "expected_tool": "create_reservation",
                "required_response": None,
                "waiting_for": ["purpose"],
                "context_preserve": True,
                "preserve_fields": ["date", "start_time", "end_time", "lab_id", "participant_count"],
                "auto_fill": True,
            },
        )

    return "", None


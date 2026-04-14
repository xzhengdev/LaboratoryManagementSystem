from datetime import date, datetime, time

from .exceptions import AppError


def require_fields(payload, fields):
    # 检查请求体里是否缺少必要字段。
    missing = [field for field in fields if payload.get(field) in (None, "")]
    if missing:
        raise AppError(f"缺少必要参数: {', '.join(missing)}")


def parse_date(value, field_name="date"):
    # 统一把 YYYY-MM-DD 字符串解析为 date 对象。
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError as exc:
        raise AppError(f"{field_name} 格式应为 YYYY-MM-DD") from exc


def parse_time(value, field_name="time"):
    # 统一把 HH:MM 字符串解析为 time 对象。
    if isinstance(value, time):
        return value
    try:
        return datetime.strptime(str(value), "%H:%M").time()
    except ValueError as exc:
        raise AppError(f"{field_name} 格式应为 HH:MM") from exc

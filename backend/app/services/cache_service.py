"""
Redis 缓存工具模块
用于实验室预约排班和统计数据的高效缓存管理
"""

import json
from datetime import date

from flask import current_app

import app.extensions as app_extensions

# 缓存键前缀常量
LAB_SCHEDULE_CACHE_PREFIX = "cache:lab_schedule:"  # 实验室排班缓存前缀
STATISTICS_CACHE_PREFIX = "cache:statistics:"      # 统计数据缓存前缀


def _redis_client():
    """获取 Redis 客户端实例
    
    Returns:
        Redis客户端对象，如果未配置则返回 None
    """
    return app_extensions.redis_client


def _safe_json_loads(raw):
    """安全的 JSON 反序列化
    
    Args:
        raw: JSON 字符串
    
    Returns:
        解析后的 Python 对象，解析失败返回 None
    """
    try:
        value = json.loads(raw)
        return value
    except Exception:
        return None


def _safe_json_dumps(value):
    """安全的 JSON 序列化
    
    Args:
        value: 要序列化的 Python 对象
    
    Returns:
        JSON 字符串，序列化失败返回 None
    """
    try:
        # ensure_ascii=False 支持中文，separators 移除多余空格压缩体积
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        return None


def _get_ttl(config_key, default_value):
    """从配置中获取缓存 TTL（生存时间）
    
    Args:
        config_key: Flask 配置项键名
        default_value: 默认 TTL 秒数
    
    Returns:
        TTL 秒数，最小为 1 秒
    """
    try:
        return max(1, int(current_app.config.get(config_key, default_value)))
    except Exception:
        return default_value


def lab_schedule_cache_key(lab_id, reservation_date, campus_id=None):
    """生成实验室排班缓存的键名
    
    Args:
        lab_id: 实验室 ID
        reservation_date: 预约日期
        campus_id: 校区 ID（可选，None 表示全局）
    
    Returns:
        缓存键字符串，格式: cache:lab_schedule:{校区或all}:{实验室ID}:{日期}
    
    Example:
        >>> lab_schedule_cache_key(100, date(2026, 4, 29), campus_id=1)
        'cache:lab_schedule:1:100:2026-04-29'
    """
    if isinstance(reservation_date, date):
        date_text = reservation_date.isoformat()
    else:
        date_text = str(reservation_date)
    # campus_id 为 None 时使用 "all" 表示跨校区查询
    campus_part = "all" if campus_id is None else str(campus_id)
    return f"{LAB_SCHEDULE_CACHE_PREFIX}{campus_part}:{lab_id}:{date_text}"


def get_cached_lab_schedule(lab_id, reservation_date, campus_id=None):
    """获取缓存的实验室排班数据
    
    Args:
        lab_id: 实验室 ID
        reservation_date: 预约日期
        campus_id: 校区 ID（可选）
    
    Returns:
        缓存的排班数据，未命中或异常返回 None
    """
    client = _redis_client()
    if client is None:
        return None
    
    key = lab_schedule_cache_key(lab_id, reservation_date, campus_id=campus_id)
    try:
        raw = client.get(key)
        if not raw:
            return None
        return _safe_json_loads(raw)
    except Exception:
        return None


def set_cached_lab_schedule(lab_id, reservation_date, payload, campus_id=None):
    """设置实验室排班缓存
    
    Args:
        lab_id: 实验室 ID
        reservation_date: 预约日期
        payload: 要缓存的数据（会被序列化为 JSON）
        campus_id: 校区 ID（可选）
    
    Note:
        缓存 TTL 由配置项 LAB_SCHEDULE_CACHE_TTL_SECONDS 控制，默认 30 秒
    """
    client = _redis_client()
    if client is None:
        return
    
    key = lab_schedule_cache_key(lab_id, reservation_date, campus_id=campus_id)
    serialized = _safe_json_dumps(payload)
    if not serialized:
        return
    
    ttl = _get_ttl("LAB_SCHEDULE_CACHE_TTL_SECONDS", 30)
    try:
        client.setex(key, ttl, serialized)
    except Exception:
        return


def invalidate_lab_schedule_cache(lab_id, reservation_date=None, campus_id=None):
    """清除实验室排班缓存
    
    Args:
        lab_id: 实验室 ID
        reservation_date: 预约日期（可选）
            - 如果指定：只删除该日期的缓存
            - 如果为 None：删除该实验室所有日期的缓存
        campus_id: 校区 ID（可选）
    
    Example:
        # 删除特定日期的缓存
        invalidate_lab_schedule_cache(100, date(2026, 4, 29))
        
        # 删除该实验室所有缓存
        invalidate_lab_schedule_cache(100)
    """
    client = _redis_client()
    if client is None:
        return
    
    # 场景1：删除指定日期的缓存（精确删除）
    if reservation_date is not None:
        key = lab_schedule_cache_key(lab_id, reservation_date, campus_id=campus_id)
        try:
            client.delete(key)
        except Exception:
            return
        return
    
    # 场景2：删除该实验室所有日期的缓存（模糊匹配批量删除）
    campus_part = "all" if campus_id is None else str(campus_id)
    pattern = f"{LAB_SCHEDULE_CACHE_PREFIX}{campus_part}:{lab_id}:*"
    try:
        # scan_iter 游标迭代，避免 keys * 阻塞 Redis
        for key in client.scan_iter(match=pattern, count=200):
            client.delete(key)
    except Exception:
        return


def statistics_cache_key(name, campus_id=None):
    """生成统计数据的缓存键名
    
    Args:
        name: 统计指标名称（如 "reservation_overview", "asset_summary"）
        campus_id: 校区 ID（可选，None 表示全校汇总）
    
    Returns:
        缓存键字符串，格式: cache:statistics:{指标名}:{校区或all}
    
    Example:
        >>> statistics_cache_key("daily_report_rate", campus_id=1)
        'cache:statistics:daily_report_rate:1'
    """
    campus_key = "all" if campus_id is None else str(campus_id)
    return f"{STATISTICS_CACHE_PREFIX}{name}:{campus_key}"


def get_cached_statistics(name, campus_id=None):
    """获取缓存的统计数据
    
    Args:
        name: 统计指标名称
        campus_id: 校区 ID（可选）
    
    Returns:
        缓存的统计数据，未命中或异常返回 None
    """
    client = _redis_client()
    if client is None:
        return None
    
    key = statistics_cache_key(name, campus_id)
    try:
        raw = client.get(key)
        if not raw:
            return None
        return _safe_json_loads(raw)
    except Exception:
        return None


def set_cached_statistics(name, campus_id, payload):
    """设置统计数据缓存
    
    Args:
        name: 统计指标名称
        campus_id: 校区 ID
        payload: 要缓存的数据（会被序列化为 JSON）
    
    Note:
        缓存 TTL 由配置项 STATISTICS_CACHE_TTL_SECONDS 控制，默认 45 秒
    """
    client = _redis_client()
    if client is None:
        return
    
    key = statistics_cache_key(name, campus_id)
    serialized = _safe_json_dumps(payload)
    if not serialized:
        return
    
    ttl = _get_ttl("STATISTICS_CACHE_TTL_SECONDS", 45)
    try:
        client.setex(key, ttl, serialized)
    except Exception:
        return


def invalidate_statistics_cache():
    """清除所有统计数据缓存
    
    适用场景：
    - 当预算数据变更时
    - 当审批状态变更时
    - 当日报审核完成时
    - 定时任务重新生成快照前
    
    Note:
        使用 scan_iter 避免 keys * 命令阻塞 Redis
    """
    client = _redis_client()
    if client is None:
        return
    
    pattern = f"{STATISTICS_CACHE_PREFIX}*"
    try:
        # 游标遍历所有匹配的键并逐个删除
        for key in client.scan_iter(match=pattern, count=200):
            client.delete(key)
    except Exception:
        return


# ============= 使用示例 =============
"""
# 1. 缓存实验室排班（在查询接口中使用）
def get_lab_schedule(lab_id, date, campus_id):
    # 先查缓存
    cached = get_cached_lab_schedule(lab_id, date, campus_id)
    if cached is not None:
        return cached
    
    # 缓存未命中，查数据库
    data = query_from_db(lab_id, date, campus_id)
    
    # 写入缓存
    set_cached_lab_schedule(lab_id, date, data, campus_id)
    return data

# 2. 预约变更时清除缓存（在创建/取消预约时调用）
def create_reservation(request):
    # ... 业务逻辑
    invalidate_lab_schedule_cache(lab_id, reservation_date, campus_id)

# 3. 统计数据缓存（在统计接口中使用）
def get_campus_overview(campus_id):
    cached = get_cached_statistics("campus_overview", campus_id)
    if cached:
        return cached
    
    data = compute_heavy_statistics(campus_id)
    set_cached_statistics("campus_overview", campus_id, data)
    return data
"""
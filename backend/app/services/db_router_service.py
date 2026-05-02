"""
多校区数据库路由模块
支持不同校区使用独立数据库，中心汇总库单独配置
"""

import json
from contextlib import contextmanager
from threading import RLock

from flask import current_app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.extensions import db

_ENGINE_CACHE = {}           # 数据库引擎缓存
_SESSION_FACTORY_CACHE = {}  # Session工厂缓存
_CACHE_LOCK = RLock()        # 线程锁


def _routing_enabled():
    """检查是否开启分库路由功能"""
    return bool(current_app.config.get("ENABLE_CAMPUS_DB_ROUTING", False))


def _parse_campus_db_uri_map():
    """解析配置中的校区数据库映射，返回 {校区ID: 数据库URI}"""
    raw = current_app.config.get("CAMPUS_DB_URI_MAP")
    if isinstance(raw, dict):
        source = raw
    else:
        text = str(raw or "").strip()
        if not text:
            return {}
        try:
            source = json.loads(text)
        except Exception:
            current_app.logger.warning("CAMPUS_DB_URI_MAP 不是有效 JSON，已忽略")
            return {}

    result = {}
    for key, value in (source or {}).items():
        try:
            campus_id = int(key)
        except Exception:
            continue
        uri = str(value or "").strip()
        if uri:
            result[campus_id] = uri
    return result


def get_routed_campus_ids():
    """获取所有配置了独立数据库的校区ID列表"""
    return sorted(_parse_campus_db_uri_map().keys())


def _get_engine(uri):
    """根据URI获取数据库引擎（带缓存）"""
    if uri in _ENGINE_CACHE:
        return _ENGINE_CACHE[uri]
    with _CACHE_LOCK:
        if uri in _ENGINE_CACHE:
            return _ENGINE_CACHE[uri]
        engine = create_engine(uri, pool_pre_ping=True)
        _ENGINE_CACHE[uri] = engine
        return engine


def _get_session_factory(uri):
    """根据URI获取Session工厂（带缓存）"""
    if uri in _SESSION_FACTORY_CACHE:
        return _SESSION_FACTORY_CACHE[uri]
    with _CACHE_LOCK:
        if uri in _SESSION_FACTORY_CACHE:
            return _SESSION_FACTORY_CACHE[uri]
        factory = sessionmaker(bind=_get_engine(uri), autoflush=True, autocommit=False)
        _SESSION_FACTORY_CACHE[uri] = factory
        return factory


def _resolve_campus_uri(campus_id):
    """根据校区ID解析对应的数据库URI"""
    if not _routing_enabled():
        return ""
    try:
        cid = int(campus_id)
    except Exception:
        return ""
    return _parse_campus_db_uri_map().get(cid, "")


@contextmanager
def campus_db_session(campus_id):
    """
    获取指定校区的数据库会话
    - 如果开启分库且配置了独立库：返回该校区专属 Session
    - 否则：回退到默认 db.session
    """
    uri = _resolve_campus_uri(campus_id)
    if not uri:
        yield db.session
        return

    session = _get_session_factory(uri)()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def summary_db_session():
    """
    获取中心汇总库的数据库会话
    - 如果配置了 SUMMARY_DB_URL：返回汇总库 Session
    - 否则：回退到默认 db.session
    """
    uri = str(current_app.config.get("SUMMARY_DB_URL") or "").strip()
    if not uri:
        yield db.session
        return

    session = _get_session_factory(uri)()
    try:
        yield session
    finally:
        session.close()


def find_across_campuses(model_class, item_id, campus_ids=None):
    """在所有校区库中按 ID 查找记录，返回 (item, campus_id) 或 (None, None)。"""
    if campus_ids is None:
        campus_ids = get_routed_campus_ids()
    if not campus_ids:
        with campus_db_session(0) as session:
            item = session.get(model_class, int(item_id))
            return (item, 0) if item else (None, None)
    for cid in campus_ids:
        with campus_db_session(cid) as session:
            item = session.get(model_class, int(item_id))
            if item is not None:
                return item, cid
    return None, None


def aggregate_across_campuses(model_class, filters_fn, campus_ids=None):
    """聚合所有校区库的查询结果，返回合并后的列表。"""
    if campus_ids is None:
        campus_ids = get_routed_campus_ids()
    if not campus_ids:
        with campus_db_session(0) as session:
            return filters_fn(session)
    rows = []
    for cid in campus_ids:
        with campus_db_session(cid) as session:
            rows.extend(filters_fn(session))
    return rows
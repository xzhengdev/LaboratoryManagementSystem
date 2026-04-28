import json
from contextlib import contextmanager
from threading import RLock

from flask import current_app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.extensions import db

_ENGINE_CACHE = {}
_SESSION_FACTORY_CACHE = {}
_CACHE_LOCK = RLock()


def _routing_enabled():
    return bool(current_app.config.get("ENABLE_CAMPUS_DB_ROUTING", False))


def _parse_campus_db_uri_map():
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
    return sorted(_parse_campus_db_uri_map().keys())


def _get_engine(uri):
    if uri in _ENGINE_CACHE:
        return _ENGINE_CACHE[uri]
    with _CACHE_LOCK:
        if uri in _ENGINE_CACHE:
            return _ENGINE_CACHE[uri]
        engine = create_engine(uri, pool_pre_ping=True)
        _ENGINE_CACHE[uri] = engine
        return engine


def _get_session_factory(uri):
    if uri in _SESSION_FACTORY_CACHE:
        return _SESSION_FACTORY_CACHE[uri]
    with _CACHE_LOCK:
        if uri in _SESSION_FACTORY_CACHE:
            return _SESSION_FACTORY_CACHE[uri]
        factory = sessionmaker(bind=_get_engine(uri), autoflush=True, autocommit=False)
        _SESSION_FACTORY_CACHE[uri] = factory
        return factory


def _resolve_campus_uri(campus_id):
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
    根据 campus_id 选择数据库会话：
    - 开启分库且配置了该校区 URI：返回独立 SQLAlchemy Session
    - 否则：回退到 Flask 默认 db.session
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
    中心汇总库会话：
    - 配置 SUMMARY_DB_URL 时写入汇总库
    - 否则回退默认库
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

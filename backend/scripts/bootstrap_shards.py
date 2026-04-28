import json
import os
import sys
from typing import Dict

from sqlalchemy import create_engine

CURRENT_DIR = os.path.dirname(__file__)
BACKEND_ROOT = os.path.dirname(CURRENT_DIR)
if BACKEND_ROOT not in sys.path:
    # Allow running `python scripts/bootstrap_shards.py` directly.
    sys.path.insert(0, BACKEND_ROOT)

from app import create_app
from app.extensions import db
from app.models import *  # noqa: F401,F403  # ensure all model tables are registered


def parse_campus_db_map(raw: str) -> Dict[int, str]:
    text = str(raw or "").strip()
    if not text:
        return {}
    try:
        data = json.loads(text)
    except Exception as exc:
        raise RuntimeError("CAMPUS_DB_URI_MAP 不是合法 JSON") from exc

    result = {}
    for key, value in (data or {}).items():
        try:
            campus_id = int(key)
        except Exception:
            continue
        uri = str(value or "").strip()
        if uri:
            result[campus_id] = uri
    return result


def ensure_schema(uri: str):
    engine = create_engine(uri, pool_pre_ping=True)
    db.metadata.create_all(bind=engine)


def main():
    app = create_app()
    with app.app_context():
        enabled = bool(app.config.get("ENABLE_CAMPUS_DB_ROUTING", False))
        campus_map = parse_campus_db_map(app.config.get("CAMPUS_DB_URI_MAP", ""))
        summary_uri = str(app.config.get("SUMMARY_DB_URL") or "").strip()

        if not enabled:
            print("[WARN] ENABLE_CAMPUS_DB_ROUTING=0，当前处于单库模式")

        if not campus_map:
            raise RuntimeError("未配置 CAMPUS_DB_URI_MAP，无法初始化校区分库")

        print(f"[INFO] 检测到 {len(campus_map)} 个校区分库配置")
        for campus_id in sorted(campus_map.keys()):
            print(f"[INFO] 初始化校区 {campus_id} 数据库结构...")
            ensure_schema(campus_map[campus_id])
            print(f"[OK] 校区 {campus_id} 初始化完成")

        if summary_uri:
            print("[INFO] 初始化中心汇总库结构...")
            ensure_schema(summary_uri)
            print("[OK] 中心汇总库初始化完成")
        else:
            print("[WARN] 未配置 SUMMARY_DB_URL，跳过中心汇总库初始化")

        print("[DONE] 分库初始化完成")


if __name__ == "__main__":
    main()

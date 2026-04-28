import json
import os
import sys

CURRENT_DIR = os.path.dirname(__file__)
BACKEND_ROOT = os.path.dirname(CURRENT_DIR)
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app import create_app
from app.extensions import db
from app.models import Campus


def parse_campus_db_map(raw: str):
    text = str(raw or "").strip()
    if not text:
        return {}
    try:
        data = json.loads(text)
    except Exception:
        return {}
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


def main():
    app = create_app()
    with app.app_context():
        rows = db.session.query(Campus).order_by(Campus.id.asc()).all()
        cfg_map = parse_campus_db_map(app.config.get("CAMPUS_DB_URI_MAP", ""))

        print("[DB] 当前默认库校区:")
        if not rows:
            print("  (空)")
        for row in rows:
            print(f"  id={row.id}, name={row.campus_name}")

        print("\n[ENV] CAMPUS_DB_URI_MAP keys:")
        if not cfg_map:
            print("  (未配置)")
        else:
            print("  " + ", ".join(str(k) for k in sorted(cfg_map.keys())))

        db_ids = {row.id for row in rows}
        cfg_ids = set(cfg_map.keys())
        missing = sorted(db_ids - cfg_ids)
        extra = sorted(cfg_ids - db_ids)

        print("\n[CHECK]")
        print(f"  in_db_not_in_map: {missing}")
        print(f"  in_map_not_in_db: {extra}")

        if missing or extra:
            print("\n[WARN] 分库路由 key 与默认库 campus_id 不一致，请调整 CAMPUS_DB_URI_MAP")
        else:
            print("\n[OK] 分库路由 key 与默认库 campus_id 一致")


if __name__ == "__main__":
    main()

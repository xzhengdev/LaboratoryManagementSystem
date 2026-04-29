import os
import sys

CURRENT_DIR = os.path.dirname(__file__)
BACKEND_ROOT = os.path.dirname(CURRENT_DIR)
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app import create_app
import app.extensions as app_extensions


def _onoff(value):
    return "ON" if value else "OFF"


def main():
    app = create_app()
    with app.app_context():
        cfg = app.config
        print("[RUNTIME SWITCHES]")
        print(f"ENABLE_CAMPUS_DB_ROUTING={_onoff(cfg.get('ENABLE_CAMPUS_DB_ROUTING'))}")
        print(f"ENABLE_DISTRIBUTED_LOCK={_onoff(cfg.get('ENABLE_DISTRIBUTED_LOCK'))}")
        print(f"ENABLE_IDEMPOTENCY={_onoff(cfg.get('ENABLE_IDEMPOTENCY'))}")
        print(f"ENABLE_RATE_LIMIT={_onoff(cfg.get('ENABLE_RATE_LIMIT'))}")
        print(f"ENABLE_ASYNC_EVENTS={_onoff(cfg.get('ENABLE_ASYNC_EVENTS'))}")
        print(f"REDIS_URL={'SET' if str(cfg.get('REDIS_URL') or '').strip() else 'EMPTY'}")
        print(f"REDIS_CONNECTED={_onoff(app_extensions.redis_client is not None)}")
        print(f"SEAWEEDFS_CAMPUS_CONFIG_MAP={'SET' if str(cfg.get('SEAWEEDFS_CAMPUS_CONFIG_MAP') or '').strip() else 'EMPTY'}")
        print(f"SUMMARY_DB_URL={'SET' if str(cfg.get('SUMMARY_DB_URL') or '').strip() else 'EMPTY'}")


if __name__ == "__main__":
    main()

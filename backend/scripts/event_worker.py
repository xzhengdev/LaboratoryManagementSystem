import argparse
import json
import os
import sys
import time


CURRENT_DIR = os.path.dirname(__file__)
BACKEND_ROOT = os.path.dirname(CURRENT_DIR)
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)


from app import create_app
import app.extensions as app_extensions
from app.extensions import db
from app.models import OperationLog, User
from app.services.summary_sync_service import sync_campus_summary_snapshots


SUPPORTED_EVENTS = {
    "reservation.created",
    "reservation.cancelled",
    "reservation.approved",
    "reservation.rejected",
    "asset.request.created",
    "asset.request.approved",
    "asset.request.rejected",
    "asset.stocked_in",
    "daily_report.created",
    "daily_report.approved",
    "daily_report.rejected",
    "file.uploaded",
}


def build_parser():
    parser = argparse.ArgumentParser(description="Async event queue worker")
    parser.add_argument("--worker-name", default="worker-1")
    parser.add_argument("--once", action="store_true", help="Consume one message then exit")
    parser.add_argument("--idle-sleep", type=float, default=0.5)
    return parser


def parse_event(raw):
    try:
        event = json.loads(raw)
        if isinstance(event, dict):
            return event
    except Exception:
        return None
    return None


def resolve_actor_user_id(payload):
    user_id = payload.get("user_id")
    if user_id is not None:
        try:
            uid = int(user_id)
            if User.query.get(uid):
                return uid
        except Exception:
            pass

    # Fallback to the first existing user to satisfy not-null FK.
    first_user = User.query.order_by(User.id.asc()).first()
    return first_user.id if first_user else None


def handle_event(app, event, worker_name):
    event_type = str(event.get("type") or "").strip()
    payload = event.get("payload") or {}

    if event_type not in SUPPORTED_EVENTS:
        app.logger.info("[%s] ignored event type: %s", worker_name, event_type)
        return False

    actor_user_id = resolve_actor_user_id(payload)
    if actor_user_id is None:
        app.logger.warning("[%s] no available user found for operation_logs", worker_name)
        return False

    detail = {
        "source": "async_event_worker",
        "event_type": event_type,
        "occurred_at": event.get("occurred_at"),
        "payload": payload,
        "worker_name": worker_name,
    }

    row = OperationLog(
        user_id=actor_user_id,
        module="async_event",
        action=event_type,
        detail=json.dumps(detail, ensure_ascii=False),
    )
    db.session.add(row)
    db.session.commit()

    campus_id = payload.get("campus_id")
    try:
        if campus_id is not None:
            sync_campus_summary_snapshots(target_campus_ids=[campus_id])
        else:
            sync_campus_summary_snapshots()
    except Exception as exc:
        app.logger.warning(
            "[%s] summary sync after event failed, event_type=%s, campus_id=%s, error=%s",
            worker_name,
            event_type,
            campus_id,
            exc,
        )

    app.logger.info("[%s] processed event: %s", worker_name, event_type)
    return True


def run_worker(args):
    app = create_app()
    with app.app_context():
        if not app.config.get("ENABLE_ASYNC_EVENTS", False):
            raise RuntimeError("ENABLE_ASYNC_EVENTS is disabled")

        redis_client = app_extensions.redis_client
        if redis_client is None:
            raise RuntimeError("Redis client is unavailable, cannot consume async events")

        queue_name = str(app.config.get("ASYNC_EVENT_QUEUE_NAME", "lab:events"))
        block_timeout = max(1, int(app.config.get("ASYNC_EVENT_BLOCK_TIMEOUT_SECONDS", 5)))
        app.logger.info("[%s] start consuming queue=%s", args.worker_name, queue_name)

        while True:
            item = redis_client.blpop(queue_name, timeout=block_timeout)
            if not item:
                if args.once:
                    break
                time.sleep(max(0.0, args.idle_sleep))
                continue

            _, raw = item
            event = parse_event(raw)
            if event is None:
                app.logger.warning("[%s] invalid event payload: %s", args.worker_name, raw)
                continue

            try:
                handle_event(app, event, args.worker_name)
            except Exception as exc:
                db.session.rollback()
                app.logger.exception("[%s] event processing failed: %s", args.worker_name, exc)

            if args.once:
                break


if __name__ == "__main__":
    run_worker(build_parser().parse_args())

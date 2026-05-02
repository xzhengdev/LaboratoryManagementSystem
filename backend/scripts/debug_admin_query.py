import argparse
import json
import os
import sys

CURRENT_DIR = os.path.dirname(__file__)
BACKEND_ROOT = os.path.dirname(CURRENT_DIR)
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app import create_app
from app.models import User
from app.services import admin_nl_query_service as svc


def parse_args():
    parser = argparse.ArgumentParser(description="Debug admin natural language query")
    parser.add_argument("--domain", default="daily_reports", choices=["daily_reports", "assets"])
    parser.add_argument("--message", required=True, help="natural language query")
    parser.add_argument("--role", default="system_admin", help="user role to simulate")
    parser.add_argument("--username", default="", help="exact username (optional)")
    parser.add_argument("--context", default="{}", help='json string, e.g. {"mode":"requests"}')
    parser.add_argument("--show-items", type=int, default=3, help="how many matched rows to preview")
    return parser.parse_args()


def select_user(role: str, username: str):
    if username:
        user = User.query.filter_by(username=username).first()
        if user:
            return user
    return User.query.filter_by(role=role).first()


def main():
    args = parse_args()
    try:
        context = json.loads(args.context or "{}")
        if not isinstance(context, dict):
            context = {}
    except Exception:
        context = {}

    app = create_app()
    with app.app_context():
        user = select_user(args.role, args.username)
        if not user:
            raise RuntimeError(f"未找到可用用户 role={args.role} username={args.username}")

        print("========== DEBUG START ==========")
        print(f"user: id={user.id}, username={user.username}, role={user.role}, campus_id={user.campus_id}")
        print(f"domain: {args.domain}")
        print(f"message: {args.message}")
        print(f"context: {json.dumps(context, ensure_ascii=False)}")

        fallback = svc._fallback_plan(args.domain, args.message, context)
        print("\n[1] fallback plan")
        print(json.dumps(fallback, ensure_ascii=False, indent=2))

        merged_plan = svc._plan_query(args.domain, args.message, context)
        print("\n[2] merged plan (fallback + llm)")
        print(json.dumps(merged_plan, ensure_ascii=False, indent=2))

        result = svc.query_admin_data(user, args.domain, args.message, context)
        print("\n[3] final query result meta")
        print(json.dumps(result.get("meta") or {}, ensure_ascii=False, indent=2))

        print("\n[4] final filters returned to frontend")
        print(json.dumps(result.get("filters") or {}, ensure_ascii=False, indent=2))

        items = result.get("items") or []
        print(f"\n[5] matched rows preview: {len(items)} rows in current response payload")
        for idx, row in enumerate(items[: max(0, args.show_items)], start=1):
            report_date = row.get("report_date")
            status = row.get("status")
            reporter = row.get("reporter_name") or row.get("requester_name") or "--"
            campus = row.get("campus_name") or "--"
            print(f"  {idx}. date={report_date}, status={status}, reporter={reporter}, campus={campus}")

        print("========== DEBUG END ==========")


if __name__ == "__main__":
    main()

import argparse
import json
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, timedelta

import requests


def build_parser():
    parser = argparse.ArgumentParser(description="Reservation concurrency benchmark")
    parser.add_argument("--base-url", default="http://127.0.0.1:5000", help="Backend base URL")
    parser.add_argument("--username", default="student1")
    parser.add_argument("--password", default="123456")
    parser.add_argument("--concurrency", type=int, default=50)
    parser.add_argument("--total", type=int, default=200)
    parser.add_argument("--campus-id", type=int, required=True)
    parser.add_argument("--lab-id", type=int, required=True)
    parser.add_argument("--date", default=(date.today() + timedelta(days=2)).isoformat())
    parser.add_argument("--start-time", default="09:00")
    parser.add_argument("--end-time", default="10:00")
    parser.add_argument("--participant-count", type=int, default=1)
    parser.add_argument("--purpose", default="并发压测")
    parser.add_argument(
        "--idempotency-mode",
        choices=["none", "same", "unique"],
        default="unique",
        help="none:不传幂等键; same:所有请求同一幂等键; unique:每次请求唯一幂等键",
    )
    parser.add_argument("--timeout", type=float, default=10.0)
    return parser


def login(base_url, username, password, timeout):
    resp = requests.post(
        f"{base_url.rstrip('/')}/api/auth/login",
        json={"username": username, "password": password},
        timeout=timeout,
    )
    resp.raise_for_status()
    payload = resp.json()
    if payload.get("code") != 0:
        raise RuntimeError(f"login failed: {payload}")
    token = (payload.get("data") or {}).get("access_token") or (
        payload.get("data") or {}
    ).get("token")
    if not token:
        raise RuntimeError("login succeeded but no access_token")
    return token


def make_task_fn(args, token):
    session = requests.Session()
    lock = threading.Lock()
    sequence = {"n": 0}
    same_key = f"bench-same-{int(time.time() * 1000)}"

    def next_index():
        with lock:
            sequence["n"] += 1
            return sequence["n"]

    def task():
        idx = next_index()
        purpose = args.purpose if args.idempotency_mode == "same" else f"{args.purpose}-{idx}"
        payload = {
            "campus_id": args.campus_id,
            "lab_id": args.lab_id,
            "reservation_date": args.date,
            "start_time": args.start_time,
            "end_time": args.end_time,
            "purpose": purpose,
            "participant_count": args.participant_count,
        }
        headers = {"Authorization": f"Bearer {token}"}
        if args.idempotency_mode == "same":
            headers["Idempotency-Key"] = same_key
        elif args.idempotency_mode == "unique":
            headers["Idempotency-Key"] = f"bench-{int(time.time() * 1000)}-{idx}"

        started = time.perf_counter()
        try:
            resp = session.post(
                f"{args.base_url.rstrip('/')}/api/reservations",
                json=payload,
                headers=headers,
                timeout=args.timeout,
            )
            latency_ms = (time.perf_counter() - started) * 1000
            try:
                data = resp.json()
            except Exception:
                data = {"raw": resp.text}
            return {
                "http_status": resp.status_code,
                "latency_ms": latency_ms,
                "body": data,
            }
        except Exception as exc:
            latency_ms = (time.perf_counter() - started) * 1000
            return {
                "http_status": 0,
                "latency_ms": latency_ms,
                "body": {"error": str(exc)},
            }

    return task


def percentile(values, p):
    if not values:
        return 0.0
    values = sorted(values)
    idx = int((len(values) - 1) * p)
    return float(values[idx])


def main():
    args = build_parser().parse_args()
    token = login(args.base_url, args.username, args.password, args.timeout)
    task_fn = make_task_fn(args, token)

    results = []
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as pool:
        futures = [pool.submit(task_fn) for _ in range(max(1, args.total))]
        for fut in as_completed(futures):
            results.append(fut.result())
    elapsed = time.perf_counter() - started

    http_counter = Counter(item["http_status"] for item in results)
    business_counter = Counter()
    reservation_ids = []
    latencies = [item["latency_ms"] for item in results]

    for item in results:
        body = item.get("body") or {}
        code = body.get("code")
        business_counter[code] += 1
        data = body.get("data") if isinstance(body, dict) else None
        if isinstance(data, dict) and data.get("id") is not None:
            reservation_ids.append(data["id"])

    unique_ids = len(set(reservation_ids))
    duplicate_count = len(reservation_ids) - unique_ids

    summary = {
        "params": {
            "concurrency": args.concurrency,
            "total": args.total,
            "idempotency_mode": args.idempotency_mode,
            "target_slot": f"{args.date} {args.start_time}-{args.end_time}",
            "lab_id": args.lab_id,
            "campus_id": args.campus_id,
        },
        "timing": {
            "elapsed_seconds": round(elapsed, 3),
            "throughput_rps": round(len(results) / elapsed, 2) if elapsed > 0 else 0.0,
            "latency_ms": {
                "p50": round(percentile(latencies, 0.50), 2),
                "p95": round(percentile(latencies, 0.95), 2),
                "p99": round(percentile(latencies, 0.99), 2),
                "max": round(max(latencies) if latencies else 0.0, 2),
            },
        },
        "http_status_distribution": dict(sorted(http_counter.items(), key=lambda x: x[0])),
        "business_code_distribution": dict(
            sorted((str(k), v) for k, v in business_counter.items())
        ),
        "reservation_write_result": {
            "returned_records": len(reservation_ids),
            "unique_reservation_ids": unique_ids,
            "duplicate_id_count": duplicate_count,
        },
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

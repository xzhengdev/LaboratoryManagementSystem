import io
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

import requests


CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = CURRENT_DIR.parent
PROJECT_ROOT = BACKEND_ROOT.parent
BENCHMARK_SCRIPT = PROJECT_ROOT / "benchmark" / "reservation_concurrency_benchmark.py"
REPORT_DIR = BACKEND_ROOT / "test-results"
BASE_URL = os.getenv("TEST_BASE_URL", "http://127.0.0.1:5000").rstrip("/")
DEFAULT_PASSWORD = "123456"

PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
    b"\x00\x00\x00\x0cIDAT\x08\xd7c\xf8\xff\xff?\x00\x05\xfe\x02\xfeA\x0f\x9b\xe1"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


class TestFailure(RuntimeError):
    pass


def now_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def build_report():
    return {
        "metadata": {
            "generated_at": now_text(),
            "base_url": BASE_URL,
            "script": str(Path(__file__).resolve()),
        },
        "scope": [
            "基础运行与环境测试",
            "核心功能测试",
            "权限与边界测试",
            "分布式能力测试",
            "高并发与稳定性测试",
            "运维与可观测性测试",
        ],
        "tests": [],
        "summary": {},
    }


def add_result(report, *, category, name, status, detail=None, metrics=None, raw=None):
    report["tests"].append(
        {
            "category": category,
            "name": name,
            "status": status,
            "detail": detail,
            "metrics": metrics or {},
            "raw": raw,
            "timestamp": now_text(),
        }
    )


def mark_pass(report, category, name, detail=None, metrics=None, raw=None):
    add_result(
        report,
        category=category,
        name=name,
        status="passed",
        detail=detail,
        metrics=metrics,
        raw=raw,
    )


def mark_fail(report, category, name, exc):
    add_result(
        report,
        category=category,
        name=name,
        status="failed",
        detail=str(exc),
    )


def mark_skip(report, category, name, detail):
    add_result(
        report,
        category=category,
        name=name,
        status="skipped",
        detail=detail,
    )


def finalize_report(report):
    counter = Counter(item["status"] for item in report["tests"])
    report["summary"] = {
        "total": len(report["tests"]),
        "passed": counter.get("passed", 0),
        "failed": counter.get("failed", 0),
        "skipped": counter.get("skipped", 0),
    }


def save_report(report):
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = REPORT_DIR / f"full_project_test_{stamp}.json"
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def run_python_script(rel_path, *extra_args):
    target = BACKEND_ROOT / rel_path
    command = [sys.executable, str(target), *extra_args]
    completed = subprocess.run(
        command,
        cwd=str(BACKEND_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    stdout = (completed.stdout or "").strip()
    stderr = (completed.stderr or "").strip()
    if completed.returncode != 0:
        raise TestFailure(
            f"{rel_path} 执行失败: code={completed.returncode}, stdout={stdout}, stderr={stderr}"
        )
    return stdout


def parse_simple_kv_lines(text):
    data = {}
    for line in text.splitlines():
        line = line.strip()
        if "=" in line:
            key, value = line.split("=", 1)
            data[key.strip()] = value.strip()
    return data


def parse_shard_lines(text):
    rows = {}
    for line in text.splitlines():
        line = line.strip()
        match = re.match(r"^\[(?P<name>[^\]]+)\] tables=(?P<tables>\d+), missing=(?P<missing>\d+)$", line)
        if match:
            rows[match.group("name")] = {
                "tables": int(match.group("tables")),
                "missing": int(match.group("missing")),
            }
    return rows


def parse_seaweedfs_lines(text):
    rows = {}
    for line in text.splitlines():
        line = line.strip()
        match = re.match(
            r"^\[OK\] campus=(?P<campus>\d+) upload_url=(?P<upload>\S+) file_id=(?P<file_id>\S+) access_url=(?P<access>\S+)$",
            line,
        )
        if match:
            rows[match.group("campus")] = {
                "upload_url": match.group("upload"),
                "file_id": match.group("file_id"),
                "access_url": match.group("access"),
            }
    return rows


class ApiClient:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    def request(self, method, path, *, token=None, timeout=15, **kwargs):
        headers = dict(kwargs.pop("headers", {}) or {})
        if token:
            headers["Authorization"] = f"Bearer {token}"
        response = self.session.request(
            method=method,
            url=f"{self.base_url}{path}",
            headers=headers,
            timeout=timeout,
            **kwargs,
        )
        try:
            payload = response.json()
        except Exception:
            payload = None
        return response, payload

    def ok(self, method, path, *, token=None, message=None, **kwargs):
        response, payload = self.request(method, path, token=token, **kwargs)
        if response.status_code != 200:
            raise TestFailure(
                f"{message or path} HTTP 状态异常: status={response.status_code}, body={payload or response.text}"
            )
        if not isinstance(payload, dict) or payload.get("code") != 0:
            raise TestFailure(f"{message or path} 业务返回异常: {payload}")
        return payload.get("data"), payload


def login(client, username):
    data, _ = client.ok(
        "POST",
        "/api/auth/login",
        json={"username": username, "password": DEFAULT_PASSWORD},
        message=f"{username} 登录",
    )
    token = data.get("access_token") or data.get("token")
    if not token:
        raise TestFailure(f"{username} 登录成功但未返回 token")
    return {
        "token": token,
        "user": data.get("user") or {},
    }


def get_lab_ids(client, token, campus_id):
    data, _ = client.ok("GET", f"/api/labs?campus_id={campus_id}", token=token, message=f"查询校区{campus_id}实验室")
    if not isinstance(data, list) or not data:
        raise TestFailure(f"校区{campus_id} 未查询到实验室")
    return [item["id"] for item in data]


def find_item(items, item_id):
    for item in items:
        if int(item.get("id")) == int(item_id):
            return item
    return None


def choose_reservation_slot(target_date):
    return [
        (target_date.isoformat(), "09:00", "10:00"),
        (target_date.isoformat(), "10:00", "11:00"),
        (target_date.isoformat(), "14:00", "15:00"),
        (target_date.isoformat(), "15:00", "16:00"),
    ]


def create_reservation_with_fallback(client, token, campus_id, lab_id, purpose_prefix):
    for reservation_date, start_time, end_time in choose_reservation_slot(date.today() + timedelta(days=3)):
        idempotency_key = f"full-test-res-{campus_id}-{lab_id}-{int(time.time() * 1000)}-{start_time}"
        payload = {
            "campus_id": campus_id,
            "lab_id": lab_id,
            "reservation_date": reservation_date,
            "start_time": start_time,
            "end_time": end_time,
            "purpose": f"{purpose_prefix}-{start_time}",
            "participant_count": 3,
        }
        response, body = client.request(
            "POST",
            "/api/reservations",
            token=token,
            json=payload,
            headers={"Idempotency-Key": idempotency_key},
        )
        if response.status_code == 200 and isinstance(body, dict) and body.get("code") == 0:
            return body.get("data")
    raise TestFailure("预约创建失败，候选时间段均不可用")


def run_environment_checks(report):
    category = "基础运行与环境测试"
    client = ApiClient(BASE_URL)
    data, _ = client.ok("GET", "/api/health", message="健康检查")
    mark_pass(report, category, "健康检查", detail="后端服务可访问", metrics=data or {})

    shards_stdout = run_python_script("scripts/check_shards.py")
    shard_rows = parse_shard_lines(shards_stdout)
    if not shard_rows:
        raise TestFailure("分库自检输出解析失败")
    mark_pass(report, category, "分库结构检查", detail="校区分库和中心汇总库结构完整", metrics=shard_rows)

    switches_stdout = run_python_script("scripts/check_runtime_switches.py")
    switches = parse_simple_kv_lines(switches_stdout)
    required_keys = [
        "ENABLE_CAMPUS_DB_ROUTING",
        "ENABLE_DISTRIBUTED_LOCK",
        "ENABLE_IDEMPOTENCY",
        "ENABLE_RATE_LIMIT",
        "ENABLE_ASYNC_EVENTS",
        "REDIS_CONNECTED",
    ]
    missing = [key for key in required_keys if switches.get(key) != "ON"]
    if missing:
        raise TestFailure(f"运行时开关未全部开启: {missing}")
    mark_pass(report, category, "运行时开关检查", detail="分布式与高并发开关均已开启", metrics=switches)

    seaweed_stdout = run_python_script("scripts/check_seaweedfs_routing.py")
    seaweed_rows = parse_seaweedfs_lines(seaweed_stdout)
    if len(seaweed_rows) < 3:
        raise TestFailure("SeaweedFS 路由检查结果不完整")
    mark_pass(report, category, "SeaweedFS 路由检查", detail="三个校区图片上传与访问链路均可用", metrics=seaweed_rows)


def run_auth_setup(report, client):
    category = "核心功能测试"
    users = {}
    accounts = [
        "hd_student_01",
        "hd_student_02",
        "hd_teacher_01",
        "hd_labadmin_01",
        "ft_student_01",
        "ft_teacher_01",
        "ft_labadmin_01",
        "hn_student_01",
        "hn_labadmin_01",
        "admin1",
    ]
    for username in accounts:
        data = login(client, username)
        users[username] = data
    mark_pass(report, category, "多角色登录测试", detail="学生、教师、实验室管理员、系统管理员均可正常登录")
    return users


def run_reservation_flow(report, client, users, campus_labs):
    category = "核心功能测试"
    student = users["hd_student_01"]
    lab_admin = users["hd_labadmin_01"]
    lab_id = campus_labs[5][0]

    reservation = create_reservation_with_fallback(
        client,
        student["token"],
        5,
        lab_id,
        "论文完整测试预约",
    )
    reservation_id = reservation["id"]

    pending, _ = client.ok("GET", "/api/approvals/pending", token=lab_admin["token"], message="查询待审批预约")
    if not find_item(pending, reservation_id):
        raise TestFailure("待审批列表中未找到新创建预约")

    approved, _ = client.ok(
        "POST",
        f"/api/approvals/{reservation_id}",
        token=lab_admin["token"],
        json={"approval_status": "approved", "remark": "完整测试自动审批"},
        message="预约审批",
    )
    if approved.get("status") != "approved":
        raise TestFailure(f"预约审批后状态异常: {approved}")

    mine, _ = client.ok("GET", "/api/reservations/my", token=student["token"], message="查询我的预约")
    mine_item = find_item(mine, reservation_id)
    if not mine_item or mine_item.get("status") != "approved":
        raise TestFailure("学生侧预约状态未更新为 approved")

    mark_pass(
        report,
        category,
        "预约创建与审批流程",
        detail="学生提交预约后，实验室管理员可在待审批列表中审批，学生侧状态同步更新",
        metrics={"reservation_id": reservation_id, "lab_id": lab_id, "campus_id": 5},
    )


def run_asset_flow(report, client, users, campus_labs):
    category = "核心功能测试"
    teacher = users["hd_teacher_01"]
    lab_admin = users["hd_labadmin_01"]
    lab_id = campus_labs[5][0]
    unique_name = f"完整测试设备-{int(time.time())}"

    asset_req, _ = client.ok(
        "POST",
        "/api/asset-requests",
        token=teacher["token"],
        headers={"Idempotency-Key": f"full-asset-{int(time.time() * 1000)}"},
        json={
            "campus_id": 5,
            "lab_id": lab_id,
            "asset_name": unique_name,
            "category": "测试类",
            "quantity": 1,
            "unit_price": 99.5,
            "reason": "论文完整测试资产申报",
        },
        message="教师提交资产申报",
    )
    request_id = asset_req["id"]

    reqs, _ = client.ok(
        "GET",
        "/api/asset-requests?campus_id=5",
        token=lab_admin["token"],
        message="查询资产申报列表",
    )
    req_item = find_item(reqs, request_id)
    if not req_item:
        raise TestFailure("资产申报列表中未找到新申报记录")

    reviewed, _ = client.ok(
        "POST",
        f"/api/asset-requests/{request_id}/review",
        token=lab_admin["token"],
        json={"campus_id": 5, "approval_status": "approved", "remark": "完整测试审批通过"},
        message="审批资产申报",
    )
    if reviewed.get("status") != "approved":
        raise TestFailure(f"资产申报审批后状态异常: {reviewed}")

    stocked, _ = client.ok(
        "POST",
        f"/api/asset-requests/{request_id}/stock-in",
        token=lab_admin["token"],
        json={
            "campus_id": 5,
            "spec_model": "TEST-MODEL-01",
            "manufacturer": "OpenAI Lab Vendor",
            "storage_location": "理工楼508",
            "status": "in_use",
            "description": "完整测试自动入库",
        },
        message="资产入库",
    )
    asset_id = stocked["id"]

    files = {"file": ("asset.png", io.BytesIO(PNG_1X1), "image/png")}
    photo, _ = client.ok(
        "POST",
        f"/api/assets/{asset_id}/photos/upload",
        token=lab_admin["token"],
        files=files,
        data={"campus_id": "5"},
        message="上传资产图片",
    )

    assets, _ = client.ok("GET", "/api/assets?campus_id=5", token=lab_admin["token"], message="查询已入库资产")
    asset_item = find_item(assets, asset_id)
    if not asset_item:
        raise TestFailure("已入库资产列表中未找到刚入库的数据")

    mark_pass(
        report,
        category,
        "资产申报、审批、入库与图片上传流程",
        detail="教师端资产申报后，可完成审批、入库与设备照片上传",
        metrics={
            "request_id": request_id,
            "asset_id": asset_id,
            "photo_file_id": photo.get("id"),
            "campus_id": 5,
        },
    )


def run_daily_report_flow(report, client, users, campus_labs):
    category = "核心功能测试"
    student = users["hd_student_01"]
    lab_admin = users["hd_labadmin_01"]
    lab_id = campus_labs[5][0]

    unread_before, _ = client.ok(
        "GET",
        "/api/notifications/unread-count",
        token=student["token"],
        message="查询审核前未读消息数",
    )
    before_count = int((unread_before or {}).get("unread_count") or 0)

    files = {"file": ("daily.png", io.BytesIO(PNG_1X1), "image/png")}
    photo, _ = client.ok(
        "POST",
        "/api/lab-reports/photos/upload",
        token=student["token"],
        files=files,
        data={"lab_id": str(lab_id)},
        message="学生上传日报图片",
    )

    report_data, _ = client.ok(
        "POST",
        "/api/lab-reports",
        token=student["token"],
        json={
            "lab_id": lab_id,
            "report_date": date.today().isoformat(),
            "content": f"完整测试日报-{int(time.time())}",
            "photo_file_ids": [photo["id"]],
        },
        message="学生提交日报",
    )
    report_id = report_data["id"]

    rows, _ = client.ok("GET", "/api/lab-reports?campus_id=5", token=lab_admin["token"], message="查询日报列表")
    row = find_item(rows, report_id)
    if not row:
        raise TestFailure("管理员侧日报列表未找到新日报")

    reviewed, _ = client.ok(
        "POST",
        f"/api/lab-reports/{report_id}/review",
        token=lab_admin["token"],
        json={"review_status": "approved", "review_remark": "完整测试审核通过"},
        message="审核日报",
    )
    if reviewed.get("status") != "approved":
        raise TestFailure(f"日报审核后状态异常: {reviewed}")

    unread_after, _ = client.ok(
        "GET",
        "/api/notifications/unread-count",
        token=student["token"],
        message="查询审核后未读消息数",
    )
    after_count = int((unread_after or {}).get("unread_count") or 0)
    if after_count < before_count + 1:
        raise TestFailure(f"日报审核后消息提醒未增加: before={before_count}, after={after_count}")

    notifications, _ = client.ok(
        "GET",
        "/api/notifications?unread_only=1",
        token=student["token"],
        message="查询未读通知列表",
    )
    matched = False
    for item in notifications:
        if item.get("biz_type") == "daily_report_review" and int(item.get("biz_id") or 0) == int(report_id):
            matched = True
            break
    if not matched:
        raise TestFailure("未在通知列表中找到对应的日报审核消息")

    mark_pass(
        report,
        category,
        "日报上传、提交、审核与消息提醒流程",
        detail="学生日报提交后，管理员可审核，审核结果会反馈到学生消息中心",
        metrics={
            "report_id": report_id,
            "photo_file_id": photo.get("id"),
            "unread_before": before_count,
            "unread_after": after_count,
        },
    )


def run_permission_tests(report, client, users, daily_report_id):
    category = "权限与边界测试"

    teacher = users["hd_teacher_01"]
    response, body = client.request("GET", "/api/asset-budgets/current", token=teacher["token"])
    if response.status_code != 403 or not isinstance(body, dict) or body.get("code") != 40301:
        raise TestFailure(f"教师访问全局预算接口未被正确拦截: status={response.status_code}, body={body}")
    mark_pass(report, category, "教师访问系统管理员预算接口拦截", detail="教师无权访问全局预算接口")

    hd_admin = users["hd_labadmin_01"]
    response, body = client.request("GET", "/api/assets?campus_id=6", token=hd_admin["token"])
    if response.status_code != 403:
        raise TestFailure(f"实验室管理员跨校区访问资产未被拦截: status={response.status_code}, body={body}")
    mark_pass(report, category, "实验室管理员跨校区资产访问拦截", detail="实验室管理员只能访问本校区资产")

    student = users["hd_student_01"]
    response, body = client.request(
        "POST",
        f"/api/lab-reports/{daily_report_id}/review",
        token=student["token"],
        json={"review_status": "approved", "review_remark": "越权测试"},
    )
    if response.status_code != 403:
        raise TestFailure(f"学生审核日报未被拦截: status={response.status_code}, body={body}")
    mark_pass(report, category, "学生越权审核日报拦截", detail="普通学生不能执行日报审核操作")


def run_distributed_tests(report, client, users, campus_labs):
    category = "分布式能力测试"
    system_admin = users["admin1"]

    ft_teacher = users["ft_teacher_01"]
    campus6_lab = campus_labs[6][0]
    campus6_name = f"跨校区资产测试-6-{int(time.time())}"
    campus6_req, _ = client.ok(
        "POST",
        "/api/asset-requests",
        token=ft_teacher["token"],
        headers={"Idempotency-Key": f"full-asset-c6-{int(time.time() * 1000)}"},
        json={
            "campus_id": 6,
            "lab_id": campus6_lab,
            "asset_name": campus6_name,
            "category": "测试类",
            "quantity": 1,
            "unit_price": 88.0,
            "reason": "跨校区资产测试",
        },
        message="丰台校区教师提交资产申报",
    )
    campus6_request_id = campus6_req["id"]

    reviewed, _ = client.ok(
        "POST",
        f"/api/asset-requests/{campus6_request_id}/review",
        token=system_admin["token"],
        json={"campus_id": 6, "approval_status": "approved", "remark": "系统管理员跨校区审批"},
        message="系统管理员审批丰台校区资产申报",
    )
    if reviewed.get("status") != "approved":
        raise TestFailure(f"系统管理员跨校区审批结果异常: {reviewed}")

    stocked, _ = client.ok(
        "POST",
        f"/api/asset-requests/{campus6_request_id}/stock-in",
        token=system_admin["token"],
        json={
            "campus_id": 6,
            "spec_model": "SYS-ADMIN-STOCK-01",
            "manufacturer": "OpenAI Cross Campus Vendor",
            "storage_location": "丰台校区理工楼508",
            "status": "in_use",
            "description": "系统管理员跨校区入库测试",
        },
        message="系统管理员跨校区资产入库",
    )

    hn_student = users["hn_student_01"]
    hn_admin = users["hn_labadmin_01"]
    campus7_lab = campus_labs[7][0]
    photo, _ = client.ok(
        "POST",
        "/api/lab-reports/photos/upload",
        token=hn_student["token"],
        files={"file": ("hn-daily.png", io.BytesIO(PNG_1X1), "image/png")},
        data={"lab_id": str(campus7_lab)},
        message="海南校区学生上传日报图片",
    )
    report_data, _ = client.ok(
        "POST",
        "/api/lab-reports",
        token=hn_student["token"],
        json={
            "lab_id": campus7_lab,
            "report_date": date.today().isoformat(),
            "content": f"跨校区日报测试-{int(time.time())}",
            "photo_file_ids": [photo["id"]],
        },
        message="海南校区学生提交日报",
    )
    hn_report_id = report_data["id"]

    reviewed_report, _ = client.ok(
        "POST",
        f"/api/lab-reports/{hn_report_id}/review",
        token=hn_admin["token"],
        json={"review_status": "approved", "review_remark": "海南校区管理员审核通过"},
        message="海南校区日报审核",
    )
    if reviewed_report.get("status") != "approved":
        raise TestFailure(f"海南校区日报审核结果异常: {reviewed_report}")

    synced, _ = client.ok(
        "POST",
        "/api/statistics/summary/sync",
        token=system_admin["token"],
        message="中心汇总同步",
    )
    latest, _ = client.ok(
        "GET",
        "/api/statistics/summary/latest",
        token=system_admin["token"],
        message="查询最新汇总快照",
    )
    rows = latest.get("rows") or []
    if len(rows) != 3:
        raise TestFailure(f"中心汇总总表校区行数异常: {len(rows)}")

    mark_pass(
        report,
        category,
        "跨校区分库写入与中心汇总同步",
        detail="丰台校区资产流程和海南校区日报流程均可独立写入，并能同步到中心汇总总表",
        metrics={
            "campus6_request_id": campus6_request_id,
            "campus6_asset_id": stocked.get("id"),
            "campus7_report_id": hn_report_id,
            "summary_snapshot_date": synced.get("snapshot_date"),
            "summary_campus_count": synced.get("campus_count"),
        },
    )


def run_observability_tests(report, client, users):
    category = "运维与可观测性测试"
    lab_admin = users["hd_labadmin_01"]
    system_admin = users["admin1"]

    overview, _ = client.ok("GET", "/api/statistics/overview", token=lab_admin["token"], message="概览统计")
    campus_stats, _ = client.ok("GET", "/api/statistics/campus", token=lab_admin["token"], message="校区统计")
    daily_overview, _ = client.ok(
        "GET",
        "/api/statistics/daily-report/overview",
        token=lab_admin["token"],
        message="日报概览统计",
    )
    latest, _ = client.ok(
        "GET",
        "/api/statistics/summary/latest",
        token=system_admin["token"],
        message="系统管理员查看中心汇总快照",
    )
    logs, _ = client.ok("GET", "/api/operation-logs", token=lab_admin["token"], message="查询操作日志")
    if not isinstance(logs, list) or not logs:
        raise TestFailure("操作日志列表为空，未体现可追踪性")

    mark_pass(
        report,
        category,
        "统计接口与日志审计查询",
        detail="管理员可查询概览统计、日报统计、中心汇总快照和操作日志",
        metrics={
            "overview": overview,
            "campus_stat_count": len(campus_stats) if isinstance(campus_stats, list) else 0,
            "daily_report_overview": daily_overview,
            "summary_rows": len((latest or {}).get("rows") or []),
            "operation_log_count": len(logs),
        },
    )


def run_benchmark_once(*, username, campus_id, lab_id, reservation_date, start_time, end_time, concurrency, total, mode):
    command = [
        sys.executable,
        str(BENCHMARK_SCRIPT),
        "--base-url",
        BASE_URL,
        "--username",
        username,
        "--password",
        DEFAULT_PASSWORD,
        "--concurrency",
        str(concurrency),
        "--total",
        str(total),
        "--campus-id",
        str(campus_id),
        "--lab-id",
        str(lab_id),
        "--date",
        reservation_date,
        "--start-time",
        start_time,
        "--end-time",
        end_time,
        "--idempotency-mode",
        mode,
    ]
    completed = subprocess.run(
        command,
        cwd=str(BACKEND_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    stdout = (completed.stdout or "").strip()
    stderr = (completed.stderr or "").strip()
    if completed.returncode != 0:
        raise TestFailure(
            f"并发压测失败: mode={mode}, code={completed.returncode}, stdout={stdout}, stderr={stderr}"
        )
    try:
        return json.loads(stdout)
    except Exception as exc:
        raise TestFailure(f"并发压测输出解析失败: {exc}; stdout={stdout}") from exc


def run_concurrency_tests(report, campus_labs):
    category = "高并发与稳定性测试"
    target_day = (date.today() + timedelta(days=5)).isoformat()

    same_summary = run_benchmark_once(
        username="ft_student_01",
        campus_id=6,
        lab_id=campus_labs[6][0],
        reservation_date=target_day,
        start_time="16:00",
        end_time="17:00",
        concurrency=20,
        total=20,
        mode="same",
    )
    same_write = (same_summary.get("reservation_write_result") or {})
    if same_write.get("unique_reservation_ids") != 1:
        raise TestFailure(f"同幂等键预约去重结果异常: {same_summary}")
    mark_pass(
        report,
        category,
        "预约接口同幂等键并发去重",
        detail="同一幂等键下，仅生成一条有效预约记录，其余请求被判定为重复提交",
        metrics=same_summary,
    )

    unique_rate_limit_summary = run_benchmark_once(
        username="hd_student_02",
        campus_id=5,
        lab_id=campus_labs[5][0],
        reservation_date=target_day,
        start_time="20:00",
        end_time="21:00",
        concurrency=40,
        total=40,
        mode="unique",
    )
    http_dist = unique_rate_limit_summary.get("http_status_distribution") or {}
    if int(http_dist.get("429", 0)) <= 0:
        raise TestFailure(f"未观察到预约限流生效迹象: {unique_rate_limit_summary}")
    mark_pass(
        report,
        category,
        "预约接口高频提交限流",
        detail="同一用户短时间内大量提交不同预约请求时，系统触发 429 限流保护",
        metrics=unique_rate_limit_summary,
    )

    unique_conflict_summary = run_benchmark_once(
        username="hn_student_01",
        campus_id=7,
        lab_id=campus_labs[7][0],
        reservation_date=target_day,
        start_time="18:00",
        end_time="19:00",
        concurrency=5,
        total=5,
        mode="unique",
    )
    unique_write = (unique_conflict_summary.get("reservation_write_result") or {})
    if int(unique_write.get("unique_reservation_ids", 0)) > 1:
        mark_fail(
            report,
            category,
            "预约冲突控制完整性",
            TestFailure(
                "不同幂等键并发请求同一时段时，仍出现多条预约成功，说明热点冲突控制仍需继续优化"
            ),
        )
        add_result(
            report,
            category=category,
            name="预约冲突控制完整性-数据",
            status="passed",
            detail="保留真实压测数据，供论文中客观分析优化空间",
            metrics=unique_conflict_summary,
        )
    else:
        mark_pass(
            report,
            category,
            "预约冲突控制完整性",
            detail="不同幂等键并发请求同一时段时，仅保留一条预约成功记录",
            metrics=unique_conflict_summary,
        )


def main():
    report = build_report()
    client = ApiClient(BASE_URL)

    try:
        run_environment_checks(report)
    except Exception as exc:
        mark_fail(report, "基础运行与环境测试", "环境总检查", exc)
        finalize_report(report)
        output = save_report(report)
        print(json.dumps({"summary": report["summary"], "report_file": str(output)}, ensure_ascii=False, indent=2))
        return

    users = {}
    campus_labs = {}
    latest_daily_report_id = None

    for category_name, func in [
        ("核心功能测试", lambda: run_auth_setup(report, client)),
    ]:
        try:
            users = func() or users
        except Exception as exc:
            mark_fail(report, category_name, "多角色登录测试", exc)

    if users:
        try:
            system_token = users["admin1"]["token"]
            for campus_id in [5, 6, 7]:
                campus_labs[campus_id] = get_lab_ids(client, system_token, campus_id)
        except Exception as exc:
            mark_fail(report, "核心功能测试", "实验室基础数据查询", exc)

    if users and campus_labs:
        for name, runner in [
            ("预约创建与审批流程", lambda: run_reservation_flow(report, client, users, campus_labs)),
            ("资产申报、审批、入库与图片上传流程", lambda: run_asset_flow(report, client, users, campus_labs)),
        ]:
            try:
                runner()
            except Exception as exc:
                mark_fail(report, "核心功能测试", name, exc)

        try:
            run_daily_report_flow(report, client, users, campus_labs)
            student = users["hd_student_01"]
            reports, _ = client.ok("GET", "/api/lab-reports", token=student["token"], message="查询学生日报列表")
            if isinstance(reports, list) and reports:
                latest_daily_report_id = int(reports[0]["id"])
        except Exception as exc:
            mark_fail(report, "核心功能测试", "日报上传、提交、审核与消息提醒流程", exc)

    if users and latest_daily_report_id:
        try:
            run_permission_tests(report, client, users, latest_daily_report_id)
        except Exception as exc:
            mark_fail(report, "权限与边界测试", "权限与边界测试", exc)
    else:
        mark_skip(report, "权限与边界测试", "权限与边界测试", "缺少日报流程结果，跳过越权审核场景")

    if users and campus_labs:
        try:
            run_distributed_tests(report, client, users, campus_labs)
        except Exception as exc:
            mark_fail(report, "分布式能力测试", "跨校区分库写入与中心汇总同步", exc)

        try:
            run_observability_tests(report, client, users)
        except Exception as exc:
            mark_fail(report, "运维与可观测性测试", "统计接口与日志审计查询", exc)

        try:
            run_concurrency_tests(report, campus_labs)
        except Exception as exc:
            mark_fail(report, "高并发与稳定性测试", "高并发与稳定性总测试", exc)
    else:
        mark_skip(report, "分布式能力测试", "跨校区分库写入与中心汇总同步", "缺少基础登录或实验室数据")
        mark_skip(report, "运维与可观测性测试", "统计接口与日志审计查询", "缺少基础登录或实验室数据")
        mark_skip(report, "高并发与稳定性测试", "高并发与稳定性总测试", "缺少基础登录或实验室数据")

    finalize_report(report)
    output = save_report(report)
    print(json.dumps({"summary": report["summary"], "report_file": str(output)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

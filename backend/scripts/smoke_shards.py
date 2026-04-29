import io
import os
import sys
import uuid
from datetime import date, timedelta

CURRENT_DIR = os.path.dirname(__file__)
BACKEND_ROOT = os.path.dirname(CURRENT_DIR)
if BACKEND_ROOT not in sys.path:
    # Allow running `python scripts/smoke_shards.py` directly.
    sys.path.insert(0, BACKEND_ROOT)

from app import create_app


PNG_1X1 = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
    b"\x00\x00\x00\x0cIDAT\x08\xd7c\xf8\xff\xff?\x00\x05\xfe\x02\xfeA\x0f\x9b\xe1"
    b"\x00\x00\x00\x00IEND\xaeB`\x82"
)


def assert_ok(resp, name):
    body = resp.get_json(silent=True) or {}
    if resp.status_code != 200 or body.get("code") != 0:
        raise RuntimeError(f"{name} 失败: status={resp.status_code}, body={body}")
    return body.get("data")


def main():
    app = create_app()
    with app.app_context():
        client = app.test_client()

        teacher_login_resp = client.post(
            "/api/auth/login",
            json={"username": "teacher1", "password": "123456"},
        )
        teacher_login_data = assert_ok(teacher_login_resp, "教师登录")
        teacher_token = teacher_login_data["token"]
        teacher_profile = teacher_login_data["user"]
        campus_id = teacher_profile.get("campus_id")
        teacher_headers = {"Authorization": f"Bearer {teacher_token}"}

        student_login_resp = client.post(
            "/api/auth/login",
            json={"username": "student1", "password": "123456"},
        )
        student_login_data = assert_ok(student_login_resp, "学生登录")
        student_token = student_login_data["token"]
        student_profile = student_login_data["user"]
        if student_profile.get("campus_id") != campus_id:
            raise RuntimeError("冒烟测试要求 student1 与 teacher1 在同一校区")
        student_headers = {"Authorization": f"Bearer {student_token}"}

        labs_resp = client.get(f"/api/labs?campus_id={campus_id}", headers=teacher_headers)
        labs = assert_ok(labs_resp, "查询实验室")
        if not labs:
            raise RuntimeError("当前校区无实验室，请先执行 seed.py + seed_shards.py")
        lab_id = labs[0]["id"]

        budget_resp = client.get("/api/asset-budgets/current", headers=teacher_headers)
        budget = assert_ok(budget_resp, "查询预算")

        target_day = (date.today() + timedelta(days=1)).isoformat()
        reservation_ok = False
        for start_time, end_time in [("10:00", "11:00"), ("11:00", "12:00"), ("14:00", "15:00")]:
            reservation_resp = client.post(
                "/api/reservations",
                headers={**teacher_headers, "Idempotency-Key": f"smoke-{uuid.uuid4().hex}"},
                json={
                    "campus_id": campus_id,
                    "lab_id": lab_id,
                    "reservation_date": target_day,
                    "start_time": start_time,
                    "end_time": end_time,
                    "purpose": "分库联调冒烟测试",
                    "participant_count": 2,
                },
            )
            if reservation_resp.status_code == 200:
                reservation_ok = True
                break

        asset_req_resp = client.post(
            "/api/asset-requests",
            headers={**teacher_headers, "Idempotency-Key": f"asset-{uuid.uuid4().hex}"},
            json={
                "campus_id": campus_id,
                "lab_id": lab_id,
                "asset_name": "测试设备",
                "category": "测试类",
                "quantity": 1,
                "unit_price": 100,
                "reason": "分库联调冒烟测试",
            },
        )
        asset_data = assert_ok(asset_req_resp, "提交资产申报")

        upload_resp = client.post(
            "/api/lab-reports/photos/upload",
            headers=student_headers,
            data={
                "lab_id": str(lab_id),
                "file": (io.BytesIO(PNG_1X1), "daily.png"),
            },
            content_type="multipart/form-data",
        )
        file_data = assert_ok(upload_resp, "上传日报图片")

        report_resp = client.post(
            "/api/lab-reports",
            headers=student_headers,
            json={
                "lab_id": lab_id,
                "report_date": date.today().isoformat(),
                "content": "分库联调冒烟测试日报",
                "photo_file_ids": [file_data["id"]],
            },
        )
        report_data = assert_ok(report_resp, "提交日报")

        print("[DONE] 冒烟测试通过")
        print(
            f"campus_id={campus_id}, lab_id={lab_id}, budget_total={budget.get('total_amount')}, "
            f"reservation_created={reservation_ok}, asset_request_id={asset_data.get('id')}, report_id={report_data.get('id')}"
        )


if __name__ == "__main__":
    main()

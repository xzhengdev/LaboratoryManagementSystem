import argparse
import os
import random
import sys
from datetime import date, datetime, timedelta

CURRENT_DIR = os.path.dirname(__file__)
BACKEND_ROOT = os.path.dirname(CURRENT_DIR)
if BACKEND_ROOT not in sys.path:
    sys.path.insert(0, BACKEND_ROOT)

from app import create_app
from app.extensions import db
from app.models import FileObject, LabDailyReport, Laboratory, User
from app.services.db_router_service import campus_db_session, get_routed_campus_ids, summary_db_session


STATUS_POOL = ["pending", "approved", "rejected"]
STATUS_WEIGHTS = [0.45, 0.4, 0.15]

CONTENT_TEMPLATES = [
    "巡查完成，实验室整体运行正常，设备摆放整齐，卫生状况良好。",
    "巡查过程中发现个别工位电源未关闭，已提醒值班同学整改。",
    "实验室门窗完好，消防通道畅通，未发现明显安全隐患。",
    "今日巡查设备运行平稳，网络连通正常，环境温湿度在合理范围。",
    "巡查发现部分桌面杂物较多，已安排现场清理并复核。",
    "巡查显示实验材料管理规范，台账记录完整，签字齐全。",
    "发现一处插线板摆放不规范，已现场调整并完成复查。",
    "实验室照明与通风正常，危险品存放区锁闭状态良好。",
]

REVIEW_REMARKS = {
    "approved": ["内容完整，情况正常", "巡查记录规范，审核通过", "信息清晰，符合要求"],
    "rejected": ["照片与文字不一致，请补充", "巡查描述过于简略，请重新提交", "缺少关键安全项说明，请完善后再提"],
}


def _parse_args():
    parser = argparse.ArgumentParser(description="Seed lab daily reports")
    parser.add_argument("--count", type=int, default=100, help="number of reports to insert")
    parser.add_argument("--seed", type=int, default=20260502, help="random seed")
    return parser.parse_args()


def _campus_ids():
    routed = get_routed_campus_ids()
    return routed if routed else [0]


def _get_reporters_by_campus(campus_id):
    reporters = []
    try:
        with summary_db_session() as session:
            rows = (
                session.query(User)
                .filter(User.status == "active", User.campus_id == campus_id, User.role == "student")
                .all()
            )
            reporters = [row.id for row in rows]
            if reporters:
                return reporters
    except Exception:
        pass

    # fallback to default db session (students only)
    rows = (
        db.session.query(User)
        .filter(User.status == "active", User.campus_id == campus_id, User.role == "student")
        .all()
    )
    reporters = [row.id for row in rows]
    if reporters:
        return reporters
    raise RuntimeError(f"校区 {campus_id} 未找到可用学生账号，无法生成日报")


def _get_reviewers_by_campus(campus_id):
    reviewer_ids = []
    try:
        with summary_db_session() as session:
            rows = (
                session.query(User)
                .filter(
                    User.status == "active",
                    User.role.in_(["lab_admin", "system_admin"]),
                    ((User.campus_id == campus_id) | (User.role == "system_admin")),
                )
                .all()
            )
            reviewer_ids = [row.id for row in rows]
            if reviewer_ids:
                return reviewer_ids
    except Exception:
        pass

    rows = (
        db.session.query(User)
        .filter(User.status == "active", User.role.in_(["lab_admin", "system_admin"]))
        .all()
    )
    reviewer_ids = [row.id for row in rows]
    if reviewer_ids:
        return reviewer_ids
    return [1]


def _get_labs(campus_id):
    with campus_db_session(campus_id) as session:
        rows = session.query(Laboratory).all()
        return rows


def _pick_source_photo(candidate_campus_ids):
    for campus_id in candidate_campus_ids:
        with campus_db_session(campus_id) as session:
            report = (
                session.query(LabDailyReport)
                .order_by(LabDailyReport.created_at.desc())
                .first()
            )
            if not report:
                continue
            photo = (
                session.query(FileObject)
                .filter_by(biz_type="daily_report_photo", biz_id=report.id, status="active")
                .order_by(FileObject.created_at.asc())
                .first()
            )
            if photo:
                return {
                    "from_campus_id": campus_id,
                    "from_report_id": report.id,
                    "file_id": photo.file_id,
                    "original_name": photo.original_name,
                    "storage_backend": photo.storage_backend,
                    "url": photo.url,
                    "mime_type": photo.mime_type,
                    "size": photo.size,
                    "sha256": photo.sha256,
                }
    return None


def _split_count(total, parts):
    if parts <= 0:
        return []
    base = total // parts
    remain = total % parts
    counts = [base] * parts
    for i in range(remain):
        counts[i] += 1
    return counts


def _random_content():
    return random.choice(CONTENT_TEMPLATES)


def _random_status():
    return random.choices(STATUS_POOL, weights=STATUS_WEIGHTS, k=1)[0]


def _insert_reports_for_campus(campus_id, count, source_photo):
    labs = _get_labs(campus_id)
    if not labs:
        return 0, 0

    reporter_ids = _get_reporters_by_campus(campus_id)
    reviewer_ids = _get_reviewers_by_campus(campus_id)

    inserted_reports = 0
    inserted_photos = 0

    with campus_db_session(campus_id) as session:
        for i in range(count):
            lab = random.choice(labs)
            reporter_id = random.choice(reporter_ids)
            status = _random_status()
            days_ago = random.randint(0, 30)
            report_date = date.today() - timedelta(days=days_ago)

            created_at = datetime.utcnow() - timedelta(days=days_ago, hours=random.randint(0, 23), minutes=random.randint(0, 59))

            row = LabDailyReport(
                campus_id=lab.campus_id,
                lab_id=lab.id,
                reporter_id=reporter_id,
                report_date=report_date,
                content=_random_content(),
                status=status,
            )
            row.created_at = created_at
            row.updated_at = created_at

            if status in {"approved", "rejected"}:
                row.reviewer_id = random.choice(reviewer_ids)
                row.review_remark = random.choice(REVIEW_REMARKS[status])
                row.reviewed_at = created_at + timedelta(hours=random.randint(1, 8))

            session.add(row)
            session.flush()
            inserted_reports += 1

            if source_photo:
                photo_row = FileObject(
                    campus_id=lab.campus_id,
                    biz_type="daily_report_photo",
                    biz_id=row.id,
                    file_id=source_photo["file_id"],
                    original_name=source_photo["original_name"] or "seed-daily-report-photo.jpg",
                    storage_backend=source_photo["storage_backend"] or "local",
                    url=source_photo["url"],
                    mime_type=source_photo["mime_type"] or "image/jpeg",
                    size=int(source_photo["size"] or 0),
                    sha256=source_photo["sha256"] or "seed_daily_report_sha256",
                    created_by=reporter_id,
                    status="active",
                )
                photo_row.created_at = created_at
                photo_row.updated_at = created_at
                session.add(photo_row)
                inserted_photos += 1

        session.commit()

    return inserted_reports, inserted_photos


def main():
    args = _parse_args()
    if args.count <= 0:
        raise ValueError("--count 必须大于 0")
    random.seed(args.seed)

    app = create_app()
    with app.app_context():
        campus_ids = _campus_ids()
        valid_campus_ids = [cid for cid in campus_ids if _get_labs(cid)]
        if not valid_campus_ids:
            raise RuntimeError("未找到可用实验室，无法生成日报数据")

        source_photo = _pick_source_photo(valid_campus_ids)
        if source_photo:
            print(
                f"[INFO] 复用图片来源: campus={source_photo['from_campus_id']} "
                f"report_id={source_photo['from_report_id']} file_id={source_photo['file_id']}"
            )
        else:
            print("[WARN] 未找到可复用的日报图片，将仅插入日报文本记录")

        distribution = _split_count(args.count, len(valid_campus_ids))
        total_reports = 0
        total_photos = 0

        for idx, campus_id in enumerate(valid_campus_ids):
            count = distribution[idx]
            inserted_reports, inserted_photos = _insert_reports_for_campus(campus_id, count, source_photo)
            total_reports += inserted_reports
            total_photos += inserted_photos
            print(f"[OK] campus={campus_id} inserted_reports={inserted_reports} inserted_photos={inserted_photos}")

        print(f"[DONE] reports={total_reports} photos={total_photos}")


if __name__ == "__main__":
    main()

from datetime import datetime
import json

from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy.orm import object_session

from app.extensions import db
from .base import BaseModel, serialize_value


class Campus(BaseModel):
    # 校区表：存储校区名称、地址和启停状态。
    __tablename__ = "campuses"

    campus_name = db.Column(db.String(100), nullable=False, unique=True)
    address = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    cover_url = db.Column(db.String(500))
    status = db.Column(db.String(20), default="active", nullable=False)

    laboratories = db.relationship("Laboratory", backref="campus", lazy=True)
    users = db.relationship("User", backref="campus", lazy=True)


class User(BaseModel):
    # 用户表：四类角色共用一张表，通过 role 区分权限。
    __tablename__ = "users"

    username = db.Column(db.String(50), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    real_name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    avatar_url = db.Column(db.String(500))
    role = db.Column(db.String(30), nullable=False)
    campus_id = db.Column(db.Integer, db.ForeignKey("campuses.id"))
    status = db.Column(db.String(20), default="active", nullable=False)

    reservations = db.relationship("Reservation", backref="user", lazy=True)
    approvals = db.relationship("Approval", backref="approver", lazy=True)

    def set_password(self, password):
        # 保存密码时只保存哈希，不保存明文。
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        # 登录时使用哈希校验密码是否正确。
        return check_password_hash(self.password_hash, password)

    def to_dict(self, extra=None):
        # 给前端额外补充 campus_name，减少联表查询次数。
        return super().to_dict(
            {
                "campus_name": self.campus.campus_name if self.campus else None,
                **(extra or {}),
            }
        )


class Laboratory(BaseModel):
    # 实验室表：记录所属校区、地点、容量与开放时间。
    __tablename__ = "laboratories"

    campus_id = db.Column(db.Integer, db.ForeignKey("campuses.id"), nullable=False)
    lab_name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(255), nullable=False)
    capacity = db.Column(db.Integer, default=0, nullable=False)
    open_time = db.Column(db.Time, nullable=False)
    close_time = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(20), default="active", nullable=False)
    description = db.Column(db.Text)
    photos = db.Column(db.Text, default="[]")

    equipment = db.relationship("Equipment", backref="lab", lazy=True)
    reservations = db.relationship("Reservation", backref="lab", lazy=True)

    def to_dict(self, extra=None):
        # 给前端额外补充 campus_name，方便列表直接显示。
        photos = []
        if self.photos:
            try:
                loaded = json.loads(self.photos)
                if isinstance(loaded, list):
                    photos = [str(item) for item in loaded if str(item).strip()]
            except Exception:
                photos = []
        return super().to_dict(
            {
                "campus_name": self.campus.campus_name if self.campus else None,
                "photos": photos,
                **(extra or {}),
            }
        )


class Equipment(BaseModel):
    # 设备表：挂在实验室下，记录设备名称、数量和状态。
    __tablename__ = "equipment"

    lab_id = db.Column(db.Integer, db.ForeignKey("laboratories.id"), nullable=False)
    equipment_name = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    status = db.Column(db.String(20), default="active", nullable=False)
    description = db.Column(db.Text)

    def to_dict(self, extra=None):
        # 额外补充实验室名称，方便管理端设备表展示。
        return super().to_dict(
            {
                "lab_name": self.lab.lab_name if self.lab else None,
                **(extra or {}),
            }
        )


class Reservation(BaseModel):
    # 预约表：记录预约人、实验室、日期、时间段、人数与审批状态。
    __tablename__ = "reservations"
    __table_args__ = (
        db.Index("idx_reservation_lab_date_status", "lab_id", "reservation_date", "status"),
        db.Index("idx_reservation_user_created_at", "user_id", "created_at"),
    )

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    campus_id = db.Column(db.Integer, db.ForeignKey("campuses.id"), nullable=False)
    lab_id = db.Column(db.Integer, db.ForeignKey("laboratories.id"), nullable=False)
    reservation_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    purpose = db.Column(db.String(255), nullable=False)
    participant_count = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(db.String(20), default="pending", nullable=False)
    need_approval = db.Column(db.Boolean, default=True, nullable=False)

    campus = db.relationship("Campus")
    approvals = db.relationship("Approval", backref="reservation", lazy=True)

    def to_dict(self, extra=None):
        # 序列化时补充用户名、校区名、实验室名，便于前端直接渲染。
        return super().to_dict(
            {
                "user_name": self.user.real_name if self.user else None,
                "campus_name": self.campus.campus_name if self.campus else None,
                "lab_name": self.lab.lab_name if self.lab else None,
                **(extra or {}),
            }
        )


class IdempotencyRecord(BaseModel):
    # 幂等记录表：防止重复提交导致重复业务写入。
    __tablename__ = "idempotency_records"
    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "endpoint",
            "idempotency_key",
            name="uq_idempotency_user_endpoint_key",
        ),
        db.Index("idx_idempotency_expires_at", "expires_at"),
    )

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    endpoint = db.Column(db.String(64), nullable=False)
    idempotency_key = db.Column(db.String(128), nullable=False)
    request_hash = db.Column(db.String(64), nullable=False)
    status = db.Column(db.String(20), default="processing", nullable=False)
    response_payload = db.Column(db.Text)
    reservation_id = db.Column(db.Integer, db.ForeignKey("reservations.id"))
    http_status = db.Column(db.Integer, default=200, nullable=False)
    error_message = db.Column(db.String(255))
    expires_at = db.Column(db.DateTime, nullable=False)

    user = db.relationship("User")


class Approval(db.Model):
    # 审批表：一条预约可以对应多条审批记录，用于追踪审批历史。
    __tablename__ = "approvals"

    id = db.Column(db.Integer, primary_key=True)
    reservation_id = db.Column(
        db.Integer, db.ForeignKey("reservations.id"), nullable=False
    )
    approver_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    approval_status = db.Column(db.String(20), nullable=False)
    remark = db.Column(db.String(255))
    approval_time = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self, extra=None):
        # 审批记录单独实现序列化，因为它没有继承 BaseModel。
        data = {
            "id": self.id,
            "reservation_id": self.reservation_id,
            "approver_id": self.approver_id,
            "approval_status": self.approval_status,
            "remark": self.remark,
            "approval_time": serialize_value(self.approval_time),
            "created_at": serialize_value(self.created_at),
        }
        if extra:
            data.update(extra)
        return data


class OperationLog(db.Model):
    # 操作日志表：用于记录关键业务动作，便于追踪与答辩演示。
    __tablename__ = "operation_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    module = db.Column(db.String(50), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    detail = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    user = db.relationship("User")

    def to_dict(self, extra=None):
        # 日志字段较少，手动序列化即可。
        data = {
            "id": self.id,
            "user_id": self.user_id,
            "module": self.module,
            "action": self.action,
            "detail": self.detail,
            "created_at": serialize_value(self.created_at),
        }
        if extra:
            data.update(extra)
        return data


class FileObject(BaseModel):
    # 文件元数据表：真实文件存储在本地目录或 SeaweedFS，这里保存索引和权限信息。
    __tablename__ = "file_objects"
    __table_args__ = (
        db.Index("idx_file_object_campus_biz", "campus_id", "biz_type", "biz_id"),
        db.Index("idx_file_object_file_id", "file_id"),
    )

    campus_id = db.Column(db.Integer, db.ForeignKey("campuses.id"), nullable=False)
    biz_type = db.Column(db.String(50), nullable=False)
    biz_id = db.Column(db.Integer)
    file_id = db.Column(db.String(255), nullable=False)
    original_name = db.Column(db.String(255), nullable=False)
    storage_backend = db.Column(db.String(30), default="local", nullable=False)
    url = db.Column(db.String(500), nullable=False)
    mime_type = db.Column(db.String(100))
    size = db.Column(db.Integer, default=0, nullable=False)
    sha256 = db.Column(db.String(64), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    status = db.Column(db.String(20), default="active", nullable=False)

    campus = db.relationship("Campus")
    uploader = db.relationship("User")

    def to_dict(self, extra=None):
        return super().to_dict(
            {
                "campus_name": self.campus.campus_name if self.campus else None,
                "uploader_name": self.uploader.real_name if self.uploader else None,
                **(extra or {}),
            }
        )


class AssetBudget(BaseModel):
    # 校区资产预算表：保存总额度、锁定额度和已使用额度。
    __tablename__ = "asset_budgets"
    __table_args__ = (
        db.UniqueConstraint("campus_id", name="uq_asset_budget_campus"),
    )

    campus_id = db.Column(db.Integer, db.ForeignKey("campuses.id"), nullable=False)
    total_amount = db.Column(db.Numeric(12, 2), default=0, nullable=False)
    locked_amount = db.Column(db.Numeric(12, 2), default=0, nullable=False)
    used_amount = db.Column(db.Numeric(12, 2), default=0, nullable=False)
    remark = db.Column(db.String(255))

    campus = db.relationship("Campus")

    def to_dict(self, extra=None):
        available = float((self.total_amount or 0) - (self.locked_amount or 0) - (self.used_amount or 0))
        return super().to_dict(
            {
                "campus_name": self.campus.campus_name if self.campus else None,
                "available_amount": available,
                **(extra or {}),
            }
        )


class AssetPurchaseRequest(BaseModel):
    # 资产购置申报表：提交申报时锁定预算，审批后转为已用或释放锁定。
    __tablename__ = "asset_purchase_requests"
    __table_args__ = (
        db.Index("idx_asset_request_campus_status", "campus_id", "status"),
        db.UniqueConstraint("request_no", name="uq_asset_request_no"),
    )

    request_no = db.Column(db.String(40), nullable=False)
    campus_id = db.Column(db.Integer, db.ForeignKey("campuses.id"), nullable=False)
    lab_id = db.Column(db.Integer, db.ForeignKey("laboratories.id"))
    requester_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    asset_name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    unit_price = db.Column(db.Numeric(12, 2), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    reason = db.Column(db.Text)
    status = db.Column(db.String(20), default="pending", nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    review_remark = db.Column(db.String(255))
    reviewed_at = db.Column(db.DateTime)

    campus = db.relationship("Campus")
    lab = db.relationship("Laboratory")
    requester = db.relationship("User", foreign_keys=[requester_id])
    reviewer = db.relationship("User", foreign_keys=[reviewer_id])

    def to_dict(self, extra=None):
        return super().to_dict(
            {
                "campus_name": self.campus.campus_name if self.campus else None,
                "lab_name": self.lab.lab_name if self.lab else None,
                "requester_name": self.requester.real_name if self.requester else None,
                "reviewer_name": self.reviewer.real_name if self.reviewer else None,
                **(extra or {}),
            }
        )


class AssetBudgetLedger(BaseModel):
    # 预算流水表：记录锁定、释放、转已用等动作，方便审计。
    __tablename__ = "asset_budget_ledgers"
    __table_args__ = (
        db.Index("idx_asset_budget_ledger_request", "request_id"),
    )

    campus_id = db.Column(db.Integer, db.ForeignKey("campuses.id"), nullable=False)
    request_id = db.Column(db.Integer, db.ForeignKey("asset_purchase_requests.id"))
    op_type = db.Column(db.String(30), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    before_locked = db.Column(db.Numeric(12, 2), nullable=False)
    after_locked = db.Column(db.Numeric(12, 2), nullable=False)
    before_used = db.Column(db.Numeric(12, 2), nullable=False)
    after_used = db.Column(db.Numeric(12, 2), nullable=False)
    operator_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    remark = db.Column(db.String(255))

    campus = db.relationship("Campus")
    request = db.relationship("AssetPurchaseRequest")
    operator = db.relationship("User")

    def to_dict(self, extra=None):
        return super().to_dict(
            {
                "campus_name": self.campus.campus_name if self.campus else None,
                "operator_name": self.operator.real_name if self.operator else None,
                **(extra or {}),
            }
        )


class AssetItem(BaseModel):
    # 资产台账表：审批通过并入库后形成正式资产记录。
    __tablename__ = "asset_items"
    __table_args__ = (
        db.Index("idx_asset_item_campus_status", "campus_id", "status"),
        db.UniqueConstraint("asset_code", name="uq_asset_code"),
    )

    asset_code = db.Column(db.String(40), nullable=False)
    campus_id = db.Column(db.Integer, db.ForeignKey("campuses.id"), nullable=False)
    lab_id = db.Column(db.Integer, db.ForeignKey("laboratories.id"))
    request_id = db.Column(db.Integer, db.ForeignKey("asset_purchase_requests.id"))
    asset_name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    price = db.Column(db.Numeric(12, 2), nullable=False)
    status = db.Column(db.String(20), default="in_use", nullable=False)
    description = db.Column(db.Text)

    campus = db.relationship("Campus")
    lab = db.relationship("Laboratory")
    request = db.relationship("AssetPurchaseRequest")

    def to_dict(self, extra=None):
        active_session = object_session(self)
        photos = []
        if active_session is not None:
            photos = (
                active_session.query(FileObject)
                .filter_by(biz_type="asset_photo", biz_id=self.id, status="active")
                .order_by(FileObject.created_at.desc())
                .all()
            )
        return super().to_dict(
            {
                "campus_name": self.campus.campus_name if self.campus else None,
                "lab_name": self.lab.lab_name if self.lab else None,
                "photos": [item.to_dict() for item in photos],
                **(extra or {}),
            }
        )


class NotificationMessage(BaseModel):
    # 站内通知表：用于小程序端提醒业务结果（如日报审核结果）。
    __tablename__ = "notification_messages"
    __table_args__ = (
        db.Index("idx_notification_user_read", "user_id", "is_read"),
        db.Index("idx_notification_campus_biz", "campus_id", "biz_type", "biz_id"),
    )

    campus_id = db.Column(db.Integer, db.ForeignKey("campuses.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.String(500), nullable=False)
    level = db.Column(db.String(20), default="info", nullable=False)
    biz_type = db.Column(db.String(50), nullable=False, default="general")
    biz_id = db.Column(db.Integer)
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    read_at = db.Column(db.DateTime)

    campus = db.relationship("Campus")
    user = db.relationship("User")

    def to_dict(self, extra=None):
        return super().to_dict(
            {
                "campus_name": self.campus.campus_name if self.campus else None,
                "user_name": self.user.real_name if self.user else None,
                **(extra or {}),
            }
        )


class LabDailyReport(BaseModel):
    # 实验室日报表：学生/教师通过小程序拍照上报，管理员审核。
    __tablename__ = "lab_daily_reports"
    __table_args__ = (
        db.Index("idx_daily_report_campus_status", "campus_id", "status"),
        db.Index("idx_daily_report_lab_date", "lab_id", "report_date"),
    )

    campus_id = db.Column(db.Integer, db.ForeignKey("campuses.id"), nullable=False)
    lab_id = db.Column(db.Integer, db.ForeignKey("laboratories.id"), nullable=False)
    reporter_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    report_date = db.Column(db.Date, nullable=False)
    content = db.Column(db.Text)
    status = db.Column(db.String(20), default="pending", nullable=False)
    reviewer_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    review_remark = db.Column(db.String(255))
    reviewed_at = db.Column(db.DateTime)

    campus = db.relationship("Campus")
    lab = db.relationship("Laboratory")
    reporter = db.relationship("User", foreign_keys=[reporter_id])
    reviewer = db.relationship("User", foreign_keys=[reviewer_id])

    def to_dict(self, extra=None):
        active_session = object_session(self)
        photos = []
        if active_session is not None:
            photos = (
                active_session.query(FileObject)
                .filter_by(biz_type="daily_report_photo", biz_id=self.id, status="active")
                .order_by(FileObject.created_at.desc())
                .all()
            )
        return super().to_dict(
            {
                "campus_name": self.campus.campus_name if self.campus else None,
                "lab_name": self.lab.lab_name if self.lab else None,
                "reporter_name": self.reporter.real_name if self.reporter else None,
                "reviewer_name": self.reviewer.real_name if self.reviewer else None,
                "photos": [item.to_dict() for item in photos],
                **(extra or {}),
            }
        )


class CampusSummarySnapshot(BaseModel):
    # 中心汇总快照表：按天聚合各校区核心业务指标，支撑总表查询与答辩演示。
    __tablename__ = "campus_summary_snapshots"
    __table_args__ = (
        db.UniqueConstraint("snapshot_date", "campus_id", name="uq_summary_snapshot_date_campus"),
        db.Index("idx_summary_snapshot_date", "snapshot_date"),
        db.Index("idx_summary_snapshot_campus", "campus_id"),
    )

    snapshot_date = db.Column(db.Date, nullable=False)
    campus_id = db.Column(db.Integer, nullable=False)
    campus_name = db.Column(db.String(100), nullable=False)

    reservation_count = db.Column(db.Integer, default=0, nullable=False)
    reservation_pending_count = db.Column(db.Integer, default=0, nullable=False)
    reservation_approved_count = db.Column(db.Integer, default=0, nullable=False)
    reservation_rejected_count = db.Column(db.Integer, default=0, nullable=False)

    asset_request_count = db.Column(db.Integer, default=0, nullable=False)
    asset_request_pending_count = db.Column(db.Integer, default=0, nullable=False)
    asset_request_approved_count = db.Column(db.Integer, default=0, nullable=False)
    asset_request_rejected_count = db.Column(db.Integer, default=0, nullable=False)

    asset_item_count = db.Column(db.Integer, default=0, nullable=False)
    asset_budget_total_amount = db.Column(db.Numeric(14, 2), default=0, nullable=False)
    asset_budget_locked_amount = db.Column(db.Numeric(14, 2), default=0, nullable=False)
    asset_budget_used_amount = db.Column(db.Numeric(14, 2), default=0, nullable=False)
    asset_budget_available_amount = db.Column(db.Numeric(14, 2), default=0, nullable=False)

    daily_report_count = db.Column(db.Integer, default=0, nullable=False)
    daily_report_pending_count = db.Column(db.Integer, default=0, nullable=False)
    daily_report_approved_count = db.Column(db.Integer, default=0, nullable=False)
    daily_report_rejected_count = db.Column(db.Integer, default=0, nullable=False)

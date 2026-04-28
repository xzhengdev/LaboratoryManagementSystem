from datetime import datetime
from decimal import Decimal

from app.extensions import db


def serialize_value(value):
    # 把 datetime / date / time 这类对象转为字符串，便于直接输出给前端。
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


class TimestampMixin:
    # 所有业务表通用的时间戳字段。
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class BaseModel(db.Model, TimestampMixin):
    __abstract__ = True

    # 所有实体表默认主键。
    id = db.Column(db.Integer, primary_key=True)

    def to_dict(self, extra=None):
        # 通用序列化方法，extra 用于补充关联字段或额外信息。
        data = {}
        for column in self.__table__.columns:
            data[column.name] = serialize_value(getattr(self, column.name))
        if extra:
            data.update(extra)
        return data

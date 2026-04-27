import uuid

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.extensions import db


class AuditLog(db.Model):
    __tablename__ = "audit_log"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_type = db.Column(db.String(120), nullable=False, index=True)
    payload = db.Column(JSONB, nullable=False)
    processed_at = db.Column(db.DateTime(timezone=True), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())

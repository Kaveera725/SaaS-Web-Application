import enum
import uuid

from sqlalchemy import Enum, Numeric, func
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.extensions import db


class PlanName(enum.Enum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class SubscriptionStatus(enum.Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    PAST_DUE = "past_due"


class Plan(db.Model):
    __tablename__ = "plans"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(
        Enum(PlanName, name="plan_name", values_callable=lambda names: [name.value for name in names]),
        nullable=False,
        unique=True,
    )
    price_monthly = db.Column(Numeric(10, 2), nullable=False)
    stripe_price_id = db.Column(db.String(255), nullable=True, unique=True)
    features = db.Column(JSONB, nullable=False, default=dict)

    subscriptions = db.relationship("Subscription", back_populates="plan", lazy="select")


class Subscription(db.Model):
    __tablename__ = "subscriptions"

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("users.id"), nullable=False, unique=True)
    plan_id = db.Column(UUID(as_uuid=True), db.ForeignKey("plans.id"), nullable=False)
    stripe_subscription_id = db.Column(db.String(255), nullable=False, unique=True)
    status = db.Column(
        Enum(
            SubscriptionStatus,
            name="subscription_status",
            values_callable=lambda statuses: [status.value for status in statuses],
        ),
        nullable=False,
        default=SubscriptionStatus.ACTIVE.value,
    )
    current_period_end = db.Column(db.DateTime(timezone=True), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, server_default=func.now())

    user = db.relationship("User", back_populates="subscription")
    plan = db.relationship("Plan", back_populates="subscriptions")

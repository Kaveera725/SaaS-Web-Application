import uuid
from datetime import datetime, timezone
from importlib import import_module
from threading import Thread

from flask import Blueprint, current_app, g, request

try:
    stripe = import_module("stripe")
except ImportError:  # pragma: no cover - handled at runtime when dependency is missing
    stripe = None

try:
    Message = import_module("flask_mail").Message
except ImportError:  # pragma: no cover - handled at runtime when dependency is missing
    Message = None

from app.extensions import db, mail
from app.models import AuditLog, Plan, PlanName, Subscription, SubscriptionStatus, User
from app.utils.decorators import login_required


billing_bp = Blueprint("billing", __name__)


def _response(success: bool, data: dict | None = None, message: str = "", status_code: int = 200):
    return {
        "success": success,
        "data": data or {},
        "message": message,
    }, status_code


def _get_stripe_customer_id_from_user_subscription(user):
    if stripe is None:
        return None

    subscription = getattr(user, "subscription", None)
    if not subscription or not subscription.stripe_subscription_id:
        return None

    try:
        stripe_subscription = stripe.Subscription.retrieve(subscription.stripe_subscription_id)
    except stripe.error.StripeError:
        return None

    return stripe_subscription.get("customer")


def _to_utc_datetime_from_unix(timestamp):
    if not timestamp:
        return datetime.now(timezone.utc)
    return datetime.fromtimestamp(int(timestamp), tz=timezone.utc)


def _send_payment_failed_email(user):
    if Message is None:
        current_app.logger.warning("Skipping payment failed email because Flask-Mail is not installed")
        return

    message = Message(
        subject="Payment failed for your subscription",
        recipients=[user.email],
        body="We could not process your latest payment. Please update your billing method in the billing portal.",
    )
    mail.send(message)


def _handle_checkout_completed(event_payload):
    session_object = event_payload.get("data", {}).get("object", {})
    metadata = session_object.get("metadata", {}) or {}

    user_id = metadata.get("user_id")
    plan_id = metadata.get("plan_id")
    stripe_subscription_id = session_object.get("subscription")

    if not user_id or not plan_id or not stripe_subscription_id:
        return

    user = User.query.filter_by(id=user_id, deleted_at=None).first()
    plan = Plan.query.filter_by(id=plan_id).first()
    if not user or not plan:
        return

    current_period_end = datetime.now(timezone.utc)
    if stripe is not None:
        try:
            stripe_subscription = stripe.Subscription.retrieve(stripe_subscription_id)
            current_period_end = _to_utc_datetime_from_unix(stripe_subscription.get("current_period_end"))
        except Exception:
            current_period_end = datetime.now(timezone.utc)

    subscription = Subscription.query.filter_by(user_id=user.id).first()
    if not subscription:
        subscription = Subscription(
            user_id=user.id,
            plan_id=plan.id,
            stripe_subscription_id=stripe_subscription_id,
            status=SubscriptionStatus.ACTIVE.value,
            current_period_end=current_period_end,
        )
        db.session.add(subscription)
    else:
        subscription.plan_id = plan.id
        subscription.stripe_subscription_id = stripe_subscription_id
        subscription.status = SubscriptionStatus.ACTIVE.value
        subscription.current_period_end = current_period_end


def _handle_invoice_payment_failed(event_payload):
    invoice_object = event_payload.get("data", {}).get("object", {})
    stripe_subscription_id = invoice_object.get("subscription")
    if not stripe_subscription_id:
        return

    subscription = Subscription.query.filter_by(stripe_subscription_id=stripe_subscription_id).first()
    if not subscription:
        return

    subscription.status = SubscriptionStatus.PAST_DUE.value
    if subscription.user:
        try:
            _send_payment_failed_email(subscription.user)
        except Exception:
            current_app.logger.exception("Failed to send payment failed email")


def _handle_subscription_deleted(event_payload):
    subscription_object = event_payload.get("data", {}).get("object", {})
    stripe_subscription_id = subscription_object.get("id")
    if not stripe_subscription_id:
        return

    subscription = Subscription.query.filter_by(stripe_subscription_id=stripe_subscription_id).first()
    if not subscription:
        return

    free_plan = Plan.query.filter(Plan.name == PlanName.FREE).first()
    if not free_plan:
        free_plan = Plan.query.filter(Plan.name == PlanName.FREE.value).first()

    subscription.status = SubscriptionStatus.CANCELLED.value
    subscription.current_period_end = _to_utc_datetime_from_unix(subscription_object.get("current_period_end"))
    if free_plan:
        subscription.plan_id = free_plan.id


def _log_audit_event(event_type, payload):
    audit_entry = AuditLog(
        event_type=event_type,
        payload=payload,
        processed_at=datetime.now(timezone.utc),
    )
    db.session.add(audit_entry)


def _process_webhook_event_async(flask_app, event_payload):
    with flask_app.app_context():
        if stripe is not None:
            stripe.api_key = flask_app.config.get("STRIPE_SECRET_KEY")

        event_type = event_payload.get("type", "unknown")
        try:
            if event_type == "checkout.session.completed":
                _handle_checkout_completed(event_payload)
            elif event_type == "invoice.payment_failed":
                _handle_invoice_payment_failed(event_payload)
            elif event_type == "customer.subscription.deleted":
                _handle_subscription_deleted(event_payload)

            _log_audit_event(event_type, event_payload)
            db.session.commit()
        except Exception:
            db.session.rollback()
            try:
                _log_audit_event(
                    event_type,
                    {
                        "error": "Failed to process webhook event",
                        "event": event_payload,
                    },
                )
                db.session.commit()
            except Exception:
                db.session.rollback()
            flask_app.logger.exception("Failed processing Stripe webhook event")


@billing_bp.post("/create-checkout-session")
@login_required
def create_checkout_session():
    payload = request.get_json(silent=True) or {}
    plan_id = payload.get("plan_id")

    if not plan_id:
        return _response(False, {}, "plan_id is required", 400)

    try:
        parsed_plan_id = uuid.UUID(str(plan_id))
    except ValueError:
        return _response(False, {}, "Invalid plan_id", 400)

    plan = Plan.query.filter_by(id=parsed_plan_id).first()
    if not plan:
        return _response(False, {}, "Plan not found", 404)

    if not plan.stripe_price_id:
        return _response(False, {}, "Selected plan is not configured for billing", 400)

    stripe_secret_key = current_app.config.get("STRIPE_SECRET_KEY")
    if not stripe_secret_key:
        return _response(False, {}, "Stripe is not configured", 500)
    if stripe is None:
        return _response(False, {}, "Stripe SDK is not installed", 500)

    stripe.api_key = stripe_secret_key

    success_url = current_app.config.get("STRIPE_CHECKOUT_SUCCESS_URL")
    cancel_url = current_app.config.get("STRIPE_CHECKOUT_CANCEL_URL")
    if not success_url or not cancel_url:
        return _response(False, {}, "Checkout URLs are not configured", 500)

    customer_id = _get_stripe_customer_id_from_user_subscription(g.user)

    checkout_payload = {
        "mode": "subscription",
        "line_items": [{"price": plan.stripe_price_id, "quantity": 1}],
        "success_url": success_url,
        "cancel_url": cancel_url,
        "client_reference_id": str(g.user.id),
        "metadata": {"user_id": str(g.user.id), "plan_id": str(plan.id)},
    }
    if customer_id:
        checkout_payload["customer"] = customer_id

    try:
        session = stripe.checkout.Session.create(**checkout_payload)
    except stripe.error.StripeError as exc:
        return _response(False, {}, f"Unable to create checkout session: {str(exc)}", 400)

    return _response(True, {"url": session.url}, "Checkout session created", 200)


@billing_bp.get("/portal")
@login_required
def create_portal_session():
    stripe_secret_key = current_app.config.get("STRIPE_SECRET_KEY")
    if not stripe_secret_key:
        return _response(False, {}, "Stripe is not configured", 500)
    if stripe is None:
        return _response(False, {}, "Stripe SDK is not installed", 500)

    stripe.api_key = stripe_secret_key

    customer_id = _get_stripe_customer_id_from_user_subscription(g.user)
    if not customer_id:
        return _response(False, {}, "No Stripe customer found for user", 400)

    return_url = current_app.config.get("STRIPE_PORTAL_RETURN_URL")
    if not return_url:
        frontend_url = (current_app.config.get("FRONTEND_URL") or "").rstrip("/")
        return_url = f"{frontend_url}/billing" if frontend_url else None

    if not return_url:
        return _response(False, {}, "Portal return URL is not configured", 500)

    try:
        portal_session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )
    except stripe.error.StripeError as exc:
        return _response(False, {}, f"Unable to create portal session: {str(exc)}", 400)

    return _response(True, {"url": portal_session.url}, "Portal session created", 200)


@billing_bp.get("/plans")
@login_required
def get_plans():
    plans = Plan.query.order_by(Plan.price_monthly.asc()).all()

    serialized_plans = [
        {
            "id": str(plan.id),
            "name": plan.name.value if hasattr(plan.name, "value") else plan.name,
            "price_monthly": float(plan.price_monthly),
            "stripe_price_id": plan.stripe_price_id,
            "features": plan.features or {},
        }
        for plan in plans
    ]

    return _response(True, {"plans": serialized_plans}, "Plans retrieved", 200)


@billing_bp.post("/webhook")
def stripe_webhook():
    if stripe is None:
        return _response(False, {}, "Stripe SDK is not installed", 500)

    stripe_secret_key = current_app.config.get("STRIPE_SECRET_KEY")
    webhook_secret = current_app.config.get("STRIPE_WEBHOOK_SECRET")
    if not stripe_secret_key or not webhook_secret:
        return _response(False, {}, "Stripe webhook is not configured", 500)

    stripe.api_key = stripe_secret_key

    payload = request.get_data(cache=False, as_text=False)
    signature = request.headers.get("Stripe-Signature", "")

    try:
        event = stripe.Webhook.construct_event(payload=payload, sig_header=signature, secret=webhook_secret)
    except (ValueError, stripe.error.SignatureVerificationError):
        return _response(False, {}, "Invalid webhook signature", 400)

    event_payload = event.to_dict_recursive() if hasattr(event, "to_dict_recursive") else dict(event)

    app_obj = current_app._get_current_object()
    Thread(target=_process_webhook_event_async, args=(app_obj, event_payload), daemon=True).start()

    return _response(True, {}, "Webhook received", 200)

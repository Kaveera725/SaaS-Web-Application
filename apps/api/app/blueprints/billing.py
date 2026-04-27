import uuid
from importlib import import_module

from flask import Blueprint, current_app, g, request

try:
    stripe = import_module("stripe")
except ImportError:  # pragma: no cover - handled at runtime when dependency is missing
    stripe = None

from app.models import Plan
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

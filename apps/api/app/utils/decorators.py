from datetime import datetime, timezone
from functools import wraps

from flask import g, jsonify
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from flask_jwt_extended.exceptions import JWTExtendedException

from app.models import SubscriptionStatus, User


def _json_response(success: bool, data: dict | None = None, message: str = "", status_code: int = 200):
    payload = {
        "success": success,
        "data": data or {},
        "message": message,
    }
    return jsonify(payload), status_code


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
        except JWTExtendedException:
            return _json_response(False, {}, "Authentication required or token expired", 401)

        user_id = get_jwt_identity()
        user = User.query.filter_by(id=user_id, deleted_at=None).first()
        if not user:
            return _json_response(False, {}, "Invalid authentication token", 401)

        g.user = user
        return fn(*args, **kwargs)

    return wrapper


def role_required(role):
    role_order = {"viewer": 1, "member": 2, "admin": 3}

    def decorator(fn):
        @wraps(fn)
        @login_required
        def wrapper(*args, **kwargs):
            user_role = g.user.role.value if hasattr(g.user.role, "value") else g.user.role
            required_role = role.value if hasattr(role, "value") else role

            if role_order.get(user_role, 0) < role_order.get(required_role, 0):
                return _json_response(False, {}, "Insufficient role permissions", 403)

            return fn(*args, **kwargs)

        return wrapper

    return decorator


def plan_required(plan):
    def decorator(fn):
        @wraps(fn)
        @login_required
        def wrapper(*args, **kwargs):
            subscription = g.user.subscription
            required_plan = plan.value if hasattr(plan, "value") else str(plan)

            if not subscription:
                return _json_response(False, {}, f"Upgrade required: {required_plan} plan", 403)

            if subscription.status != SubscriptionStatus.ACTIVE.value:
                return _json_response(False, {}, f"Upgrade required: {required_plan} plan", 403)

            period_end = subscription.current_period_end
            if period_end and period_end.tzinfo is None:
                period_end = period_end.replace(tzinfo=timezone.utc)

            if period_end and period_end < datetime.now(timezone.utc):
                return _json_response(False, {}, f"Upgrade required: {required_plan} plan", 403)

            current_plan = subscription.plan.name.value if hasattr(subscription.plan.name, "value") else subscription.plan.name
            if current_plan != required_plan:
                return _json_response(False, {}, f"Upgrade required: {required_plan} plan", 403)

            return fn(*args, **kwargs)

        return wrapper

    return decorator


def verified_required(fn):
    @wraps(fn)
    @login_required
    def wrapper(*args, **kwargs):
        if not g.user.is_verified:
            return _json_response(False, {}, "Email verification required", 403)
        return fn(*args, **kwargs)

    return wrapper

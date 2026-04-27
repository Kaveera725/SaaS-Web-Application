import uuid
from datetime import datetime, timedelta, timezone

from flask import Blueprint, current_app, jsonify, render_template, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
)
from flask_mail import Message
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from marshmallow import Schema, ValidationError, fields, validate

from app.extensions import db, mail, revoked_token_jti
from app.models import PasswordResetToken, User


auth_bp = Blueprint("auth", __name__)


class RegisterSchema(Schema):
    email = fields.Email(required=True)
    password = fields.String(required=True, validate=validate.Length(min=8, max=128))
    first_name = fields.String(required=False, allow_none=True, validate=validate.Length(max=120))
    last_name = fields.String(required=False, allow_none=True, validate=validate.Length(max=120))


class LoginSchema(Schema):
    email = fields.Email(required=True)
    password = fields.String(required=True, validate=validate.Length(min=8, max=128))
    remember_me = fields.Boolean(required=False, load_default=False)


class ForgotPasswordSchema(Schema):
    email = fields.Email(required=True)


class ResetPasswordSchema(Schema):
    token = fields.String(required=True)
    password = fields.String(required=True, validate=validate.Length(min=8, max=128))


register_schema = RegisterSchema()
login_schema = LoginSchema()
forgot_password_schema = ForgotPasswordSchema()
reset_password_schema = ResetPasswordSchema()


def _response(success: bool, data: dict | None = None, message: str = "", status_code: int = 200):
    payload = {
        "success": success,
        "data": data or {},
        "message": message,
    }
    return jsonify(payload), status_code


def _send_verification_email(user: User) -> None:
    verification_token = str(uuid.uuid4())
    current_app.logger.info(
        "Verification email queued for %s with token %s",
        user.email,
        verification_token,
    )


def _password_reset_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(
        current_app.config["SECRET_KEY"],
        salt=current_app.config.get("SECURITY_PASSWORD_SALT") or "password-reset-salt",
    )


def _send_password_reset_email(email: str, token: str) -> None:
    frontend_url = (current_app.config.get("FRONTEND_URL") or "").rstrip("/")
    reset_link = f"{frontend_url}/reset-password?token={token}" if frontend_url else f"/reset-password?token={token}"

    message = Message(
        subject="Reset your password",
        recipients=[email],
        body=render_template("emails/password_reset.txt", reset_link=reset_link),
    )
    mail.send(message)


@auth_bp.post("/register")
def register():
    try:
        payload = register_schema.load(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return _response(False, {"errors": exc.messages}, "Validation failed", 400)

    email = payload["email"].strip().lower()
    if User.query.filter_by(email=email).first():
        return _response(False, {}, "Email already exists", 400)

    user = User(
        email=email,
        first_name=payload.get("first_name"),
        last_name=payload.get("last_name"),
    )
    user.set_password(payload["password"])

    db.session.add(user)
    db.session.commit()

    _send_verification_email(user)

    return _response(True, {"user": user.to_dict()}, "Registration successful. Verification email sent.", 201)


@auth_bp.post("/login")
def login():
    try:
        payload = login_schema.load(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return _response(False, {"errors": exc.messages}, "Validation failed", 400)

    email = payload["email"].strip().lower()
    user = User.query.filter_by(email=email, deleted_at=None).first()

    if not user or not user.check_password(payload["password"]):
        return _response(False, {}, "Invalid email or password", 401)

    if not user.is_active:
        return _response(False, {}, "User account is inactive", 403)

    access_token = create_access_token(identity=str(user.id), additional_claims={"role": user.role.value if hasattr(user.role, "value") else user.role})
    refresh_token = create_refresh_token(identity=str(user.id))

    return _response(
        True,
        {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": user.to_dict(),
            "remember_me": payload.get("remember_me", False),
        },
        "Login successful",
        200,
    )


@auth_bp.post("/logout")
@jwt_required(refresh=True)
def logout():
    jti = get_jwt()["jti"]
    revoked_token_jti.add(jti)
    return _response(True, {}, "Logout successful", 200)


@auth_bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    access_token = create_access_token(identity=identity)
    return _response(True, {"access_token": access_token}, "Token refreshed", 200)


@auth_bp.post("/forgot-password")
def forgot_password():
    try:
        payload = forgot_password_schema.load(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return _response(False, {"errors": exc.messages}, "Validation failed", 400)

    email = payload["email"].strip().lower()
    user = User.query.filter_by(email=email, deleted_at=None).first()

    if user:
        serializer = _password_reset_serializer()
        signed_token = serializer.dumps({"user_id": str(user.id), "nonce": str(uuid.uuid4())})
        expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=current_app.config.get("PASSWORD_RESET_TOKEN_EXPIRES_SECONDS", 3600)
        )

        reset_token = PasswordResetToken(user_id=user.id, token=signed_token, expires_at=expires_at)
        db.session.add(reset_token)
        db.session.commit()

        _send_password_reset_email(user.email, signed_token)

    return _response(
        True,
        {},
        "If this email exists, a password reset link has been sent.",
        200,
    )


@auth_bp.post("/reset-password")
def reset_password():
    try:
        payload = reset_password_schema.load(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return _response(False, {"errors": exc.messages}, "Validation failed", 400)

    serializer = _password_reset_serializer()
    max_age_seconds = current_app.config.get("PASSWORD_RESET_TOKEN_EXPIRES_SECONDS", 3600)

    try:
        token_payload = serializer.loads(payload["token"], max_age=max_age_seconds)
    except (SignatureExpired, BadSignature):
        return _response(False, {}, "Invalid or expired reset token", 400)

    user_id = token_payload.get("user_id")
    if not user_id:
        return _response(False, {}, "Invalid or expired reset token", 400)

    now = datetime.now(timezone.utc)
    reset_token = PasswordResetToken.query.filter(
        PasswordResetToken.token == payload["token"],
        PasswordResetToken.user_id == user_id,
        PasswordResetToken.used_at.is_(None),
        PasswordResetToken.expires_at >= now,
    ).first()

    if not reset_token:
        return _response(False, {}, "Invalid or expired reset token", 400)

    user = User.query.filter_by(id=user_id, deleted_at=None).first()
    if not user:
        return _response(False, {}, "Invalid or expired reset token", 400)

    user.set_password(payload["password"])
    reset_token.used_at = now
    db.session.commit()

    return _response(True, {}, "Password reset successful", 200)

import uuid

from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
)
from marshmallow import Schema, ValidationError, fields, validate

from app.extensions import db, revoked_token_jti
from app.models import User


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


register_schema = RegisterSchema()
login_schema = LoginSchema()


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

from flask import Blueprint, jsonify


auth_bp = Blueprint("auth", __name__)


@auth_bp.get("/health")
def health():
    return jsonify({"module": "auth", "status": "ok"}), 200

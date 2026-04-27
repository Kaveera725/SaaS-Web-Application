from flask import Blueprint, jsonify


users_bp = Blueprint("users", __name__)


@users_bp.get("/health")
def health():
    return jsonify({"module": "users", "status": "ok"}), 200

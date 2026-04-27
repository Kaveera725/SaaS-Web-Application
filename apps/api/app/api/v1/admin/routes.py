from flask import Blueprint, jsonify


admin_bp = Blueprint("admin", __name__)


@admin_bp.get("/health")
def health():
    return jsonify({"module": "admin", "status": "ok"}), 200

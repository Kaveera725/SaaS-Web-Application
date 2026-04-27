from flask import Blueprint, jsonify


dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.get("/health")
def health():
    return jsonify({"module": "dashboard", "status": "ok"}), 200

from flask import Blueprint, jsonify


billing_bp = Blueprint("billing", __name__)


@billing_bp.get("/health")
def health():
    return jsonify({"module": "billing", "status": "ok"}), 200

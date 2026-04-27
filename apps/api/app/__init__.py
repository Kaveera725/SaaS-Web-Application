import os

from dotenv import load_dotenv
from flask import Flask, jsonify

from app.api.v1.auth import auth_bp
from app.api.v1.billing import billing_bp
from app.api.v1.users import users_bp
from app.config import DevelopmentConfig, ProductionConfig, TestingConfig
from app.extensions import init_extensions


def _resolve_config(config_object):
	if config_object is not None:
		return config_object

	env_name = os.getenv("FLASK_CONFIG", "development").lower()
	config_map = {
		"development": DevelopmentConfig,
		"testing": TestingConfig,
		"production": ProductionConfig,
	}
	return config_map.get(env_name, DevelopmentConfig)


def _register_blueprints(app: Flask) -> None:
	app.register_blueprint(auth_bp, url_prefix="/api/v1/auth")
	app.register_blueprint(users_bp, url_prefix="/api/v1/users")
	app.register_blueprint(billing_bp, url_prefix="/api/v1/billing")


def _register_error_handlers(app: Flask) -> None:
	@app.errorhandler(400)
	def bad_request(error):
		return jsonify({"error": "Bad Request"}), 400

	@app.errorhandler(401)
	def unauthorized(error):
		return jsonify({"error": "Unauthorized"}), 401

	@app.errorhandler(403)
	def forbidden(error):
		return jsonify({"error": "Forbidden"}), 403

	@app.errorhandler(404)
	def not_found(error):
		return jsonify({"error": "Not Found"}), 404

	@app.errorhandler(500)
	def internal_server_error(error):
		return jsonify({"error": "Internal Server Error"}), 500


def create_app(config_object=None) -> Flask:
	load_dotenv()

	app = Flask(__name__, instance_relative_config=True)
	app.config.from_object(_resolve_config(config_object))

	init_extensions(app)
	_register_blueprints(app)
	_register_error_handlers(app)

	return app

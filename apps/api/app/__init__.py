from flask import Flask

from app.api import register_api
from app.config import DevelopmentConfig, ProductionConfig, TestingConfig
from app.errors import register_error_handlers
from app.extensions import init_extensions


def create_app(config_name: str = "development") -> Flask:
	app = Flask(__name__, instance_relative_config=True)

	config_map = {
		"development": DevelopmentConfig,
		"testing": TestingConfig,
		"production": ProductionConfig,
	}
	app.config.from_object(config_map.get(config_name, DevelopmentConfig))

	init_extensions(app)
	register_api(app)
	register_error_handlers(app)

	return app

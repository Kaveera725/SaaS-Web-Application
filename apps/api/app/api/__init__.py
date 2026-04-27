from app.api.v1 import register_v1_blueprints


def register_api(app):
	register_v1_blueprints(app)

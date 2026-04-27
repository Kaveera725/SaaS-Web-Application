from app.api.v1.admin import admin_bp
from app.api.v1.auth import auth_bp
from app.api.v1.billing import billing_bp
from app.api.v1.dashboard import dashboard_bp
from app.api.v1.users import users_bp


def register_v1_blueprints(app):
	app.register_blueprint(auth_bp, url_prefix="/api/v1/auth")
	app.register_blueprint(users_bp, url_prefix="/api/v1/users")
	app.register_blueprint(dashboard_bp, url_prefix="/api/v1/dashboard")
	app.register_blueprint(billing_bp, url_prefix="/api/v1/billing")
	app.register_blueprint(admin_bp, url_prefix="/api/v1/admin")

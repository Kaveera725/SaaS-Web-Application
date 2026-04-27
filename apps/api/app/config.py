import os
from datetime import timedelta


class BaseConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.environ.get("SQLALCHEMY_DATABASE_URI")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    PASSWORD_RESET_TOKEN_EXPIRES_SECONDS = 3600
    SECURITY_PASSWORD_SALT = os.environ.get("SECURITY_PASSWORD_SALT")

    MAIL_SERVER = os.environ.get("MAIL_SERVER")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", "0")) if os.environ.get("MAIL_PORT") else None
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "false").lower() == "true"
    MAIL_USE_SSL = os.environ.get("MAIL_USE_SSL", "false").lower() == "true"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER")

    FRONTEND_URL = os.environ.get("FRONTEND_URL")
    STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY")
    STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET")
    STRIPE_CHECKOUT_SUCCESS_URL = os.environ.get("STRIPE_CHECKOUT_SUCCESS_URL")
    STRIPE_CHECKOUT_CANCEL_URL = os.environ.get("STRIPE_CHECKOUT_CANCEL_URL")
    STRIPE_PORTAL_RETURN_URL = os.environ.get("STRIPE_PORTAL_RETURN_URL")


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class TestingConfig(BaseConfig):
    TESTING = True


class ProductionConfig(BaseConfig):
    DEBUG = False

from app import create_app


def create_test_app():
    return create_app("testing")

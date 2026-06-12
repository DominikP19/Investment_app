import pytest

import app.db as app_db
from app import create_app


class FakeConnection:
    """Stands in for a psycopg connection; records executed statements."""

    def __init__(self):
        self.executed = []
        self.committed = False
        self.rolled_back = False

    def execute(self, query, params=None):
        self.executed.append((query, params))
        return self

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


@pytest.fixture
def app():
    flask_app = create_app()
    flask_app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def fake_con(monkeypatch):
    """Replace app.db.get_db with a fake connection that records queries."""
    con = FakeConnection()
    monkeypatch.setattr(app_db, "get_db", lambda: con)
    return con

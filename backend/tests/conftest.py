from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg import sql

from app.config import settings
from app.db import get_connection
from app.main import app

# Point the whole app at the test database. Every get_connection() call
# reads settings.postgres_db at call time, so this one line redirects all of them.
settings.postgres_db = settings.postgres_test_db

SCHEMA_FILE = Path(__file__).resolve().parents[1] / "sql" / "001_create_events.sql"


@pytest.fixture(scope="session", autouse=True)
def test_database():
    # Safety guard: never run destructive setup on a database not named *_test.
    assert settings.postgres_db.endswith("_test"), (
        f"Refusing to run tests on database {settings.postgres_db!r}"
    )

    with psycopg.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        user=settings.postgres_user,
        password=settings.postgres_password,
        dbname="postgres",
        autocommit=True,
    ) as admin:
        name = sql.Identifier(settings.postgres_db)
        admin.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(name))
        admin.execute(sql.SQL("CREATE DATABASE {}").format(name))

    with get_connection() as conn:
        conn.execute(SCHEMA_FILE.read_text(encoding="utf-8"))

    yield


@pytest.fixture(autouse=True)
def clean_events(test_database):
    with get_connection() as conn:
        conn.execute("TRUNCATE events RESTART IDENTITY")


@pytest.fixture
def client():
    return TestClient(app)
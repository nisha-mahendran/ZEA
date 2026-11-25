import psycopg
from psycopg.rows import dict_row

from app.config import settings


def get_connection(dbname: str | None = None) -> psycopg.Connection:
    return psycopg.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        user=settings.postgres_user,
        password=settings.postgres_password,
        dbname=dbname or settings.postgres_db,
        row_factory=dict_row,
    )
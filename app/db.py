import os
from psycopg import Connection
from psycopg.rows import dict_row

def get_db_url() -> str:
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL is not set")
    return db_url

def get_conn() -> Connection:
    return Connection.connect(get_db_url(), row_factory=dict_row)
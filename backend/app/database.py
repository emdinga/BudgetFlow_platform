from __future__ import annotations

import os

from psycopg.conninfo import make_conninfo
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


def create_pool() -> ConnectionPool:
    """Build a pool from discrete environment values without logging the password."""
    required = ("PGHOST", "PGDATABASE", "PGUSER", "PGPASSWORD")
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise RuntimeError(f"Missing required database settings: {', '.join(missing)}")

    conninfo = make_conninfo(
        host=os.environ["PGHOST"],
        port=os.getenv("PGPORT", "5432"),
        dbname=os.environ["PGDATABASE"],
        user=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
        connect_timeout=3,
        application_name="budgetflow-api",
    )
    return ConnectionPool(
        conninfo=conninfo,
        min_size=0,
        max_size=5,
        timeout=2,
        open=False,
        kwargs={"row_factory": dict_row},
    )

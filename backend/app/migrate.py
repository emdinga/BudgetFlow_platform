from __future__ import annotations

import os
import hashlib
from pathlib import Path

import psycopg
from psycopg.conninfo import make_conninfo


def main() -> None:
    migrations_dir = Path(__file__).resolve().parent.parent / "migrations"

    conninfo = make_conninfo(
        host=os.environ["PGHOST"],
        port=os.getenv("PGPORT", "5432"),
        dbname=os.environ["PGDATABASE"],
        user=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
        connect_timeout=5,
        application_name="budgetflow-migrate",
    )
    with psycopg.connect(conninfo) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                checksum TEXT NOT NULL,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        for migration in sorted(migrations_dir.glob("[0-9]*.sql")):
            content = migration.read_bytes()
            checksum = hashlib.sha256(content).hexdigest()
            version = migration.stem
            applied = conn.execute(
                "SELECT checksum FROM schema_migrations WHERE version = %s",
                (version,),
            ).fetchone()
            if applied:
                if applied[0] != checksum:
                    raise RuntimeError(f"Applied migration {version} was modified")
                continue

            statements = [part.strip() for part in content.decode("utf-8").split(";")]
            statements = [statement for statement in statements if statement]
            with conn.transaction():
                for statement in statements:
                    conn.execute(statement, prepare=False)
                conn.execute(
                    "INSERT INTO schema_migrations (version, checksum) VALUES (%s, %s)",
                    (version, checksum),
                )
    print("BudgetFlow database migrations are up to date.")


if __name__ == "__main__":
    main()

import os
import psycopg
from psycopg import sql
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("Falta DATABASE_URL")

def fetch_all(query: str, params=None):
    params = params or ()
    with psycopg.connect(DATABASE_URL, connect_timeout=10) as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()

def fetch_one(query: str, params=None):
    params = params or ()
    with psycopg.connect(DATABASE_URL, connect_timeout=10) as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchone()


def count_rows(table_name: str, schema: str = "public"):
    with psycopg.connect(DATABASE_URL, connect_timeout=10) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = %s AND table_name = %s
                );
                """,
                (schema, table_name),
            )
            exists = cur.fetchone()[0]

            if not exists:
                return None

            query = sql.SQL("SELECT COUNT(*) FROM {}.{};").format(
                sql.Identifier(schema),
                sql.Identifier(table_name),
            )
            cur.execute(query)
            row = cur.fetchone()
            return row[0] if row else 0

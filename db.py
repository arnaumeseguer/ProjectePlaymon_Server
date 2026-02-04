import os
from psycopg_pool import ConnectionPool

def _env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Falta variable d'entorn: {name}")
    return v

host = _env("PGHOST")
port = _env("PGPORT")
dbname = _env("PGDATABASE")
user = _env("PGUSER")
password = _env("PGPASSWORD")
sslmode = os.getenv("PGSSLMODE", "require")

conninfo = (
    f"host={host} "
    f"port={port} "
    f"dbname={dbname} "
    f"user={user} "
    f"password={password} "
    f"sslmode={sslmode}"
)

pool = ConnectionPool(conninfo=conninfo, min_size=0, max_size=1, open=False)

def _ensure_pool_open():
    if pool.closed:
        pool.open()

def fetch_all(query: str, params=None):
    params = params or ()
    _ensure_pool_open()
    with pool.connection(timeout=10) as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()

def fetch_one(query: str, params=None):
    params = params or ()
    _ensure_pool_open()
    with pool.connection(timeout=10) as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchone()

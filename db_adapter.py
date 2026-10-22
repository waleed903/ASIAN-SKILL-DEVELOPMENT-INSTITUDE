"""
Database compatibility layer for ASDI Portal.
Supports both PostgreSQL (Render production via DATABASE_URL) and SQLite (local fallback).
Provides a seamless interface so that existing conn.execute(...) code runs cleanly with psycopg2.
"""
import os
import re
import sqlite3

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
# Heroku/Render sometimes supply postgres:// instead of postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

try:
    import psycopg2
    import psycopg2.extras
    import psycopg2.extensions
    PSYCOPG2_AVAILABLE = True

    # Crucial: Register float casting for PostgreSQL NUMERIC / DECIMAL types
    # This prevents 'TypeError: unsupported operand type(s) for *: Decimal and float'
    # 1700 is the PostgreSQL OID for NUMERIC/DECIMAL
    DEC2FLOAT = psycopg2.extensions.new_type(
        (1700,), "DEC2FLOAT",
        lambda val, cur: float(val) if val is not None else None
    )
    psycopg2.extensions.register_type(DEC2FLOAT)

except ImportError:
    PSYCOPG2_AVAILABLE = False


def _convert_sql(sql):
    # Replace date functions
    sql = re.sub(r"date\(\s*'now'\s*,\s*'localtime'\s*\)", "CURRENT_DATE", sql, flags=re.IGNORECASE)
    sql = re.sub(r"date\(\s*'now'\s*\)", "CURRENT_DATE", sql, flags=re.IGNORECASE)
    sql = re.sub(r"datetime\(\s*'now'\s*,\s*'localtime'\s*\)", "CURRENT_TIMESTAMP", sql, flags=re.IGNORECASE)
    sql = re.sub(r"datetime\(\s*'now'\s*\)", "CURRENT_TIMESTAMP", sql, flags=re.IGNORECASE)
    sql = re.sub(r"substr\(\s*created_at\s*,\s*1\s*,\s*10\s*\)", "DATE(created_at)::text", sql, flags=re.IGNORECASE)

    # Convert is_active = 1 / 0 to boolean TRUE / FALSE for PostgreSQL compatibility
    sql = re.sub(r"\bis_active\s*=\s*1\b", "is_active = TRUE", sql, flags=re.IGNORECASE)
    sql = re.sub(r"\bis_active\s*=\s*0\b", "is_active = FALSE", sql, flags=re.IGNORECASE)

    # Tokenize by SQL string literals to only replace ? outside of quotes
    tokens = re.split(r"('(?:''|[^'])*')", sql)
    for i in range(0, len(tokens), 2):
        tokens[i] = tokens[i].replace("?", "%s")
    return "".join(tokens)


class PgCursorWrapper:
    """Wraps a psycopg2 RealDictCursor to support SQLite-like methods."""
    def __init__(self, raw_cursor):
        self._cur = raw_cursor

    def execute(self, sql, params=None):
        sql = _convert_sql(sql)
        if params is None:
            self._cur.execute(sql)
        else:
            if isinstance(params, list):
                params = tuple(params)
            self._cur.execute(sql, params)
        return self

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    def fetchmany(self, size=None):
        return self._cur.fetchmany(size) if size else self._cur.fetchmany()

    @property
    def lastrowid(self):
        try:
            return self._cur.lastrowid
        except Exception:
            return None

    def close(self):
        try:
            self._cur.close()
        except Exception:
            pass

    def __iter__(self):
        return iter(self._cur)


class PgConnectionWrapper:
    """
    Wraps psycopg2 connection to provide:
    1. conn.execute(sql, params) shorthand like sqlite3.
    2. Dict-accessible rows (like sqlite3.Row).
    3. Auto-commit or explicit commit/rollback.
    """
    def __init__(self, raw_conn):
        self._conn = raw_conn

    def cursor(self):
        raw_cur = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        return PgCursorWrapper(raw_cur)

    def execute(self, sql, params=None):
        cur = self.cursor()
        cur.execute(sql, params)
        return cur

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass


def get_db_connection(local_sqlite_path=None):
    """
    Returns an active database connection:
    - If DATABASE_URL is set and psycopg2 is available: connects to PostgreSQL.
    - Otherwise: falls back to SQLite.
    """
    if DATABASE_URL and PSYCOPG2_AVAILABLE:
        raw_conn = psycopg2.connect(DATABASE_URL)
        return PgConnectionWrapper(raw_conn)

    # SQLite fallback
    if not local_sqlite_path:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        local_sqlite_path = os.path.join(base_dir, "data", "asdi.db")

    conn = sqlite3.connect(local_sqlite_path, check_same_thread=False, timeout=20)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
    except Exception:
        pass
    return conn


def is_postgres():
    return bool(DATABASE_URL and PSYCOPG2_AVAILABLE)

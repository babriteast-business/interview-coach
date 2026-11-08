"""Database layer. Uses Postgres when DATABASE_URL is set (Render/Neon), otherwise local SQLite.
All app code writes SQLite-style '?' placeholders; this module adapts them for Postgres."""
import hashlib
import os
import re
import secrets
import sqlite3
import time
from contextlib import contextmanager

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
PG = DATABASE_URL.startswith(("postgres://", "postgresql://"))
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "interview.db")

if PG:
    import psycopg
    from psycopg.rows import dict_row

ID = "SERIAL PRIMARY KEY" if PG else "INTEGER PRIMARY KEY"
TS = "DOUBLE PRECISION" if PG else "REAL"
SCHEMA = f"""
CREATE TABLE IF NOT EXISTS users(
  id {ID}, username TEXT UNIQUE, pw_hash TEXT, salt TEXT, created {TS},
  role TEXT DEFAULT 'user', status TEXT DEFAULT 'pending', trusted INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, user_id INTEGER, created {TS});
CREATE TABLE IF NOT EXISTS profiles(user_id INTEGER PRIMARY KEY, text TEXT, updated {TS});
CREATE TABLE IF NOT EXISTS interviews(
  id {ID}, user_id INTEGER, track TEXT, category TEXT, difficulty TEXT,
  total INTEGER, created {TS}, finished INTEGER DEFAULT 0, report TEXT);
CREATE TABLE IF NOT EXISTS turns(
  id {ID}, interview_id INTEGER, user_id INTEGER, q_id TEXT, category TEXT,
  question TEXT, key_points TEXT, is_followup INTEGER DEFAULT 0, answer TEXT, score INTEGER,
  feedback TEXT, created {TS}, answered {TS});
CREATE TABLE IF NOT EXISTS code_runs(
  id {ID}, user_id INTEGER, problem_id TEXT, code TEXT, passed INTEGER, total INTEGER, created {TS});
CREATE TABLE IF NOT EXISTS threads(id {ID}, user_id INTEGER, title TEXT, created {TS});
CREATE TABLE IF NOT EXISTS messages(id {ID}, thread_id INTEGER, role TEXT, content TEXT, created {TS});
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS bank(id TEXT PRIMARY KEY, data TEXT, added {TS});
CREATE TABLE IF NOT EXISTS ai_usage(user_id INTEGER, day TEXT, n INTEGER, PRIMARY KEY(user_id, day));
"""
# columns added after v1 (for existing local databases)
MIGRATIONS = [
    "ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'",
    "ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'pending'",
    "ALTER TABLE users ADD COLUMN trusted INTEGER DEFAULT 0",
]
ID_TABLES = {"users", "interviews", "turns", "code_runs", "threads", "messages"}


class _Cur:
    def __init__(self, cur, lastrowid=None):
        self._c, self.lastrowid = cur, lastrowid

    @property
    def rowcount(self):
        return self._c.rowcount

    def fetchone(self):
        r = self._c.fetchone()
        return dict(r) if r is not None else None

    def fetchall(self):
        return [dict(r) for r in self._c.fetchall()]

    def __iter__(self):
        return iter(self.fetchall())


class _Conn:
    def __init__(self, raw):
        self.raw = raw

    def execute(self, sql, params=()):
        if not PG:
            cur = self.raw.execute(sql, params)
            return _Cur(cur, cur.lastrowid)
        sql = sql.replace("?", "%s")
        m = re.match(r"\s*INSERT INTO (\w+)", sql, re.I)
        want_id = bool(m and m.group(1).lower() in ID_TABLES and "RETURNING" not in sql.upper())
        if want_id:
            sql += " RETURNING id"
        cur = self.raw.execute(sql, params)
        if want_id:
            return _Cur(cur, cur.fetchone()["id"])
        return _Cur(cur)


def executemany(conn_obj, sql, rows):
    """Insert many rows in one go (one network round trip batch on Postgres)."""
    rows = list(rows)
    if not rows:
        return
    raw = conn_obj.raw
    if PG:
        with raw.cursor() as cur:
            cur.executemany(sql.replace("?", "%s"), rows)
    else:
        raw.executemany(sql, rows)


def _raw():
    if PG:
        return psycopg.connect(DATABASE_URL, row_factory=dict_row, connect_timeout=15)
    c = sqlite3.connect(DB_PATH, timeout=15)
    c.row_factory = sqlite3.Row
    return c


@contextmanager
def conn():
    raw = _raw()
    try:
        yield _Conn(raw)
        raw.commit()
    except Exception:
        raw.rollback()
        raise
    finally:
        raw.close()


def init():
    if not PG:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    raw = _raw()
    try:
        if PG:
            for stmt in [s for s in SCHEMA.split(";") if s.strip()]:
                raw.execute(stmt)
        else:
            raw.executescript(SCHEMA)
        raw.commit()
    finally:
        raw.close()
    for m in MIGRATIONS:          # harmless if the column already exists
        raw = _raw()
        try:
            raw.execute(m)
            raw.commit()
        except Exception:
            raw.rollback()
        finally:
            raw.close()


# ---------------- users ----------------
def hash_pw(password, salt=None):
    salt = salt or secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000).hex()
    return h, salt


def create_user(username, password, role="user", status="pending"):
    h, salt = hash_pw(password)
    with conn() as c:
        return c.execute("INSERT INTO users(username,pw_hash,salt,created,role,status,trusted) VALUES(?,?,?,?,?,?,?)",
                         (username, h, salt, time.time(), role, status, 1 if role == "admin" else 0)).lastrowid


def ensure_admin(username, password):
    """Create or reset the admin account from environment variables on every start."""
    if not username or not password:
        return False
    h, salt = hash_pw(password)
    with conn() as c:
        row = c.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
        if row:
            c.execute("UPDATE users SET pw_hash=?, salt=?, role='admin', status='active', trusted=1 WHERE id=?",
                      (h, salt, row["id"]))
        else:
            c.execute("INSERT INTO users(username,pw_hash,salt,created,role,status,trusted) VALUES(?,?,?,?,?,?,?)",
                      (username, h, salt, time.time(), "admin", "active", 1))
        # only one admin: anyone else who was admin is demoted
        c.execute("UPDATE users SET role='user' WHERE role='admin' AND username<>?", (username,))
    return True


def get_user(username):
    with conn() as c:
        return c.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()


def check_password(row, password):
    h, _ = hash_pw(password, row["salt"])
    return secrets.compare_digest(h, row["pw_hash"])


def user_count():
    with conn() as c:
        return c.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]


# ---------------- sessions ----------------
def new_session(user_id):
    token = secrets.token_urlsafe(32)
    with conn() as c:
        c.execute("INSERT INTO sessions(token,user_id,created) VALUES(?,?,?)", (token, user_id, time.time()))
    return token


def session_user(token):
    if not token:
        return None
    with conn() as c:
        row = c.execute("SELECT s.user_id, u.username, u.role, u.status, u.trusted FROM sessions s "
                        "JOIN users u ON u.id=s.user_id WHERE s.token=? AND s.created > ?",
                        (token, time.time() - 30 * 86400)).fetchone()
    if not row or row["status"] != "active":
        return None
    return row


def end_session(token):
    with conn() as c:
        c.execute("DELETE FROM sessions WHERE token=?", (token,))


# ---------------- settings & usage ----------------
def get_setting(key, default=None):
    with conn() as c:
        row = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key, value):
    with conn() as c:
        c.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                  (key, str(value)))


def usage_today(user_id):
    day = time.strftime("%Y-%m-%d")
    with conn() as c:
        row = c.execute("SELECT n FROM ai_usage WHERE user_id=? AND day=?", (user_id, day)).fetchone()
    return row["n"] if row else 0


def add_usage(user_id):
    day = time.strftime("%Y-%m-%d")
    with conn() as c:
        c.execute("INSERT INTO ai_usage(user_id,day,n) VALUES(?,?,1) "
                  "ON CONFLICT(user_id,day) DO UPDATE SET n=ai_usage.n+1", (user_id, day))

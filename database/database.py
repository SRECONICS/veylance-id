import os
import json
import hashlib
import sqlite3
from datetime import datetime

from paths import data_root


DB_PATH = os.path.join(data_root(), "veylance.db")


class Database:
    """Thin SQLite wrapper. Two tables:

    users      — one row per enrolled identity (name, averaged embedding,
                 how many samples it was built from, enrollment date).
    auth_logs  — one row per authentication *event* (not per frame — see
                 main.py, which only logs on state transitions).
    """

    def __init__(self, path=DB_PATH):

        self.path = path
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.execute("PRAGMA foreign_keys = ON")

        self._create_tables()

    def _create_tables(self):

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                embedding TEXT NOT NULL,
                sample_count INTEGER NOT NULL,
                enrolled_at TEXT NOT NULL
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS auth_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_name TEXT,
                timestamp TEXT NOT NULL,
                similarity REAL,
                liveness_result TEXT,
                result TEXT NOT NULL
            )
        """)

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        self.conn.commit()

        self._migrate_schema()

    def _migrate_schema(self):
        """Additive column migrations for databases created by earlier
        checkpoints. SQLite has no 'ADD COLUMN IF NOT EXISTS', so we just
        try and ignore the error if it's already there."""

        try:
            self.conn.execute(
                "ALTER TABLE auth_logs ADD COLUMN snapshot_path TEXT"
            )
            self.conn.commit()
        except sqlite3.OperationalError:
            pass  # column already exists

    # ================= USERS =================

    def upsert_user(self, name, embedding, sample_count):

        embedding_json = json.dumps(embedding)
        enrolled_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.conn.execute("""
            INSERT INTO users (name, embedding, sample_count, enrolled_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                embedding = excluded.embedding,
                sample_count = excluded.sample_count,
                enrolled_at = excluded.enrolled_at
        """, (name, embedding_json, sample_count, enrolled_at))

        self.conn.commit()

    def get_all_users(self):

        rows = self.conn.execute(
            "SELECT name, embedding, sample_count, enrolled_at FROM users"
        ).fetchall()

        return [
            {
                "name": row[0],
                "embedding": json.loads(row[1]),
                "sample_count": row[2],
                "enrolled_at": row[3]
            }
            for row in rows
        ]

    def user_count(self):
        return self.conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    def delete_user(self, name):
        self.conn.execute("DELETE FROM users WHERE name = ?", (name,))
        self.conn.commit()

    # ================= AUTH LOGS =================

    def log_auth_event(self, user_name, similarity, liveness_result, result, snapshot_path=None):

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.conn.execute("""
            INSERT INTO auth_logs
                (user_name, timestamp, similarity, liveness_result, result, snapshot_path)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_name, timestamp, similarity, liveness_result, result, snapshot_path))

        self.conn.commit()

    def get_recent_logs(self, limit=100):

        rows = self.conn.execute("""
            SELECT user_name, timestamp, similarity, liveness_result, result, snapshot_path
            FROM auth_logs
            ORDER BY id DESC
            LIMIT ?
        """, (limit,)).fetchall()

        return [
            {
                "user_name": row[0],
                "timestamp": row[1],
                "similarity": row[2],
                "liveness_result": row[3],
                "result": row[4],
                "snapshot_path": row[5]
            }
            for row in rows
        ]

    # ================= SETTINGS =================

    def get_setting(self, key, default=None):

        row = self.conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()

        if row is None:
            return default

        return json.loads(row[0])

    def set_setting(self, key, value):

        self.conn.execute("""
            INSERT INTO settings (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """, (key, json.dumps(value)))

        self.conn.commit()

    # ================= ENROLLMENT PIN =================
    # A PBKDF2-hashed PIN gating "Start Enrollment" — never stored in
    # plaintext. Reuses the settings table (pin_salt / pin_hash keys)
    # rather than a dedicated table, since it's a single value.

    def has_pin(self):
        return self.get_setting("pin_hash") is not None

    def set_pin(self, pin):
        salt = os.urandom(16).hex()
        pin_hash = self._hash_pin(pin, salt)
        self.set_setting("pin_salt", salt)
        self.set_setting("pin_hash", pin_hash)

    def verify_pin(self, pin):
        salt = self.get_setting("pin_salt")
        stored_hash = self.get_setting("pin_hash")

        if salt is None or stored_hash is None:
            return False

        return self._hash_pin(pin, salt) == stored_hash

    @staticmethod
    def _hash_pin(pin, salt_hex):
        salt = bytes.fromhex(salt_hex)
        derived = hashlib.pbkdf2_hmac(
            "sha256", pin.encode("utf-8"), salt, 100_000
        )
        return derived.hex()

    def close(self):
        self.conn.close()

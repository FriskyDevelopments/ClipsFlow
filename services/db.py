from __future__ import annotations

import os
import secrets
import sqlite3
from contextlib import closing
from typing import Any

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "db.sqlite3")


def get_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cursor = conn.execute(f"PRAGMA table_info({table})")
    return any(row["name"] == column for row in cursor.fetchall())


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    if not _has_column(conn, table, column):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _generate_referral_code() -> str:
    return secrets.token_urlsafe(6).replace("-", "").replace("_", "")[:10].lower()


def init_db() -> None:
    with closing(get_connection()) as conn:
        with conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    platform TEXT,
                    platform_id TEXT,
                    is_pro BOOLEAN DEFAULT 0,
                    stripe_customer_id TEXT,
                    PRIMARY KEY (platform, platform_id)
                )
                """
            )

            _ensure_column(conn, "users", "username", "TEXT")
            _ensure_column(conn, "users", "keyboard_installed", "BOOLEAN DEFAULT 0")
            _ensure_column(conn, "users", "referral_code", "TEXT")
            _ensure_column(conn, "users", "referred_by_platform_id", "TEXT")
            _ensure_column(conn, "users", "referral_count", "INTEGER DEFAULT 0")
            _ensure_column(conn, "users", "pro_referral_count", "INTEGER DEFAULT 0")
            _ensure_column(conn, "users", "commission_cents", "INTEGER DEFAULT 0")
            _ensure_column(conn, "users", "granted_for_free", "BOOLEAN DEFAULT 0")
            _ensure_column(conn, "users", "created_at", "TEXT DEFAULT CURRENT_TIMESTAMP")
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_users_referral_code ON users(referral_code)"
            )


def _get_user_locked(conn: sqlite3.Connection, platform: str, platform_id: str) -> sqlite3.Row | None:
    cursor = conn.execute(
        "SELECT * FROM users WHERE platform = ? AND platform_id = ?",
        (platform, platform_id),
    )
    return cursor.fetchone()


def get_user(platform: str, platform_id: str) -> dict[str, Any] | None:
    init_db()
    with closing(get_connection()) as conn:
        row = _get_user_locked(conn, platform, platform_id)
        return dict(row) if row else None


def _create_unique_referral_code(conn: sqlite3.Connection) -> str:
    for _ in range(5):
        code = _generate_referral_code()
        existing = conn.execute("SELECT 1 FROM users WHERE referral_code = ?", (code,)).fetchone()
        if not existing:
            return code
    raise RuntimeError("Failed to generate unique referral code")


def ensure_user(platform: str, platform_id: str, username: str | None = None) -> dict[str, Any]:
    init_db()
    with closing(get_connection()) as conn:
        with conn:
            row = _get_user_locked(conn, platform, platform_id)
            if row:
                if username and username != row["username"]:
                    conn.execute(
                        "UPDATE users SET username = ? WHERE platform = ? AND platform_id = ?",
                        (username, platform, platform_id),
                    )
                return dict(_get_user_locked(conn, platform, platform_id))

            referral_code = _create_unique_referral_code(conn)
            conn.execute(
                """
                INSERT INTO users (platform, platform_id, username, is_pro, keyboard_installed, referral_code)
                VALUES (?, ?, ?, 0, 0, ?)
                """,
                (platform, platform_id, username, referral_code),
            )
            return dict(_get_user_locked(conn, platform, platform_id))


def mark_keyboard_installed(platform: str, platform_id: str) -> None:
    init_db()
    with closing(get_connection()) as conn:
        with conn:
            conn.execute(
                "UPDATE users SET keyboard_installed = 1 WHERE platform = ? AND platform_id = ?",
                (platform, platform_id),
            )


def apply_referral_code(new_user_platform: str, new_user_platform_id: str, referral_code: str) -> bool:
    """Apply referral to a user once; returns True if applied."""
    init_db()
    with closing(get_connection()) as conn:
        with conn:
            user = _get_user_locked(conn, new_user_platform, new_user_platform_id)
            if not user:
                return False
            if user["referred_by_platform_id"]:
                return False

            inviter = conn.execute(
                "SELECT platform_id FROM users WHERE referral_code = ? AND platform = ?",
                (referral_code, new_user_platform),
            ).fetchone()
            if not inviter:
                return False

            inviter_id = inviter["platform_id"]
            if inviter_id == new_user_platform_id:
                return False

            conn.execute(
                "UPDATE users SET referred_by_platform_id = ? WHERE platform = ? AND platform_id = ?",
                (inviter_id, new_user_platform, new_user_platform_id),
            )
            conn.execute(
                "UPDATE users SET referral_count = COALESCE(referral_count, 0) + 1 WHERE platform = ? AND platform_id = ?",
                (new_user_platform, inviter_id),
            )
            return True


def set_user_pro(
    platform: str,
    platform_id: str,
    is_pro: bool,
    stripe_customer_id: str | None = None,
    granted_for_free: bool = False,
    commission_per_conversion_cents: int = 0,
) -> list[tuple[str, str]]:
    """Updates pro status and returns users who should receive an upgrade notification."""
    init_db()
    with closing(get_connection()) as conn:
        with conn:
            user = _get_user_locked(conn, platform, platform_id)
            if not user:
                referral_code = _create_unique_referral_code(conn)
                conn.execute(
                    """
                    INSERT INTO users (platform, platform_id, is_pro, keyboard_installed, referral_code)
                    VALUES (?, ?, 0, 0, ?)
                    """,
                    (platform, platform_id, referral_code),
                )
                user = _get_user_locked(conn, platform, platform_id)

            was_pro = bool(user["is_pro"])
            conn.execute(
                """
                UPDATE users
                SET is_pro = ?,
                    stripe_customer_id = COALESCE(?, stripe_customer_id),
                    granted_for_free = CASE WHEN ? THEN 1 ELSE granted_for_free END
                WHERE platform = ? AND platform_id = ?
                """,
                (is_pro, stripe_customer_id, int(granted_for_free), platform, platform_id),
            )

            if not was_pro and is_pro and user["referred_by_platform_id"]:
                conn.execute(
                    """
                    UPDATE users
                    SET pro_referral_count = COALESCE(pro_referral_count, 0) + 1,
                        commission_cents = COALESCE(commission_cents, 0) + ?
                    WHERE platform = ? AND platform_id = ?
                    """,
                    (commission_per_conversion_cents, platform, user["referred_by_platform_id"]),
                )

    return [(platform, platform_id)] if is_pro else []


def upsert_user(platform: str, platform_id: str, is_pro: bool, stripe_customer_id: str = None):
    set_user_pro(
        platform=platform,
        platform_id=platform_id,
        is_pro=is_pro,
        stripe_customer_id=stripe_customer_id,
    )


def update_user_by_customer_id(stripe_customer_id: str, is_pro: bool) -> list[tuple[str, str]]:
    """Updates user(s) matching stripe_customer_id and returns updated (platform, platform_id) pairs."""
    init_db()
    with closing(get_connection()) as conn:
        with conn:
            cur = conn.execute(
                "SELECT platform, platform_id FROM users WHERE stripe_customer_id = ?",
                (stripe_customer_id,),
            )
            users = [(row["platform"], row["platform_id"]) for row in cur.fetchall()]

            if users:
                conn.execute(
                    "UPDATE users SET is_pro = ? WHERE stripe_customer_id = ?",
                    (is_pro, stripe_customer_id),
                )

    return users


def get_referral_stats(platform: str, platform_id: str) -> dict[str, int]:
    init_db()
    with closing(get_connection()) as conn:
        row = conn.execute(
            """
            SELECT
                COALESCE(referral_count, 0) AS referral_count,
                COALESCE(pro_referral_count, 0) AS pro_referral_count,
                COALESCE(commission_cents, 0) AS commission_cents
            FROM users
            WHERE platform = ? AND platform_id = ?
            """,
            (platform, platform_id),
        ).fetchone()

    if not row:
        return {"referral_count": 0, "pro_referral_count": 0, "commission_cents": 0}

    return {
        "referral_count": int(row["referral_count"]),
        "pro_referral_count": int(row["pro_referral_count"]),
        "commission_cents": int(row["commission_cents"]),
    }


def get_admin_stats() -> dict[str, Any]:
    """Returns global system metrics for the admin terminal."""
    init_db()
    with closing(get_connection()) as conn:
        total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        total_pro = conn.execute("SELECT COUNT(*) FROM users WHERE is_pro = 1").fetchone()[0]
        total_commissions = conn.execute("SELECT SUM(commission_cents) FROM users").fetchone()[0] or 0

        return {
            "total_users": total_users,
            "total_pro": total_pro,
            "total_commissions_cents": total_commissions,
        }

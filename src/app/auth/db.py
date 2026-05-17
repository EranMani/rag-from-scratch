"""
This file defines the identity of the user.

The Connection to AI Engineering and Your Graph:

The State Anchor: The id generated here serves as the primary key LangGraph uses to retrieve the thread_id and conversation history. Without a stable identifier from the database, the agent would be unable to maintain "memory" of the user across different sessions.

Separation of Concerns: This file manages Identity (authentication), while other modules (like user_profiles) handle Mastery (knowledge tracking). This engineering separation allows you to evolve the learning model without disrupting the core user registration system.

Reliability: check_same_thread=False disables Python's thread-safety check so the connection can be shared across threads. The actual concurrency safety comes from WAL mode and proper transaction handling — check_same_thread merely removes the runtime error that would block cross-thread access.

System Integrity: By handling user creation in the authentication layer rather than the graph nodes, you ensure the agent remains a "consumer" of valid data, preventing accidental or duplicate profile generation during the RAG process.

Transaction safety - when code completes successfully, it runs commit() automatically 
                     if error found, it can perform rollback, avoid saving to db in half baked state
                     always use with() when opening a connection to the database
                     Avoid wasting resources, allows the agent to run safely and steady in production

"""


import sqlite3
import uuid
from pathlib import Path
from datetime import datetime, timezone
from app.core.config import settings


def _connect() -> sqlite3.Connection:
    path = Path(settings.sqlite_db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    # Row object — supports both row['email'] key access and row[0] index access
    conn.row_factory = sqlite3.Row
    # NOTE: Allows to read from the database while being written to it, avoiding it being locked
    # When running commit, the changes are saved into a helper called wal-file
    # It allows the agent to keep reading from the main db without waiting for the writing to be fully complete
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_user_db() -> None:
    """
    id => the user id which is later used in the agent state
    email => unique entrance identifier
    password_hash => fundamental security requirement, never store the raw plaintext password
    created_at => record the registering date
    is_admin => 1 for admin users, 0 for regular users
    """
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                display_name TEXT,
                created_at TEXT NOT NULL,
                is_admin INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        # Migration: add is_admin to existing databases that predate this column
        try:
            conn.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0")
        except Exception:
            pass  # column already exists
        conn.commit()


def create_user(email: str, password_hash: str, display_name: str | None, is_admin: bool = False) -> str:
    """Create the registered user in the system"""
    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO users (id, email, password_hash, display_name, created_at, is_admin) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, email.lower(), password_hash, display_name, now, 1 if is_admin else 0)
        )
        conn.commit()
    return user_id


def get_user_by_email(email: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, email, password_hash, display_name, created_at, is_admin FROM users WHERE email = ?",
            (email.lower(),),
        ).fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, email, password_hash, display_name, created_at, is_admin FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
    return dict(row) if row else None


def list_users() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, email, display_name, created_at, is_admin FROM users ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def seed_admin_user() -> None:
    """Ensure the built-in admin account exists. Safe to call on every startup (no-op if already present)."""
    from app.auth.password import hash_password
    if get_user_by_email("admin"):
        return
    admin_id = create_user(
        email="admin",
        password_hash=hash_password("admin"),
        display_name="Admin",
        is_admin=True,
    )
    # Create a profile so the admin can use the chat tab without errors
    try:
        from app.profile.db import create_profile
        create_profile(admin_id)
    except Exception:
        pass


def delete_user(user_id: str) -> bool:
    """Returns True if a user was removed, False if no matching row existed.

    Why this matters:
    - The API layer uses the bool to decide HTTP status: 204 No Content (success) vs 404 Not Found.
    - Cleanup logic knows the "Identity" anchor is gone before wiping associated AI mastery profiles.
    """
    with _connect() as conn:
        cur = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
    # rowcount tells how many rows the DELETE affected (1 if user existed, 0 if not)
    return cur.rowcount > 0


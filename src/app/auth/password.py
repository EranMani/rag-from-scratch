"""
Password hashing utilities using bcrypt.

Why bcrypt (and not SHA-256):
    bcrypt is intentionally slow and resource-intensive — each hash requires
    multiple rounds of computation. This makes brute-force / dictionary attacks
    orders of magnitude harder compared to fast algorithms like SHA-256, which
    can be computed billions of times per second on modern GPUs.

    SHA-256 is designed for speed (file integrity checks, signatures).
    bcrypt is designed for resistance to offline attacks on leaked databases.

Connection to the auth system and db.py:
    This file is the engine behind the `password_hash` column in the users table.

    Registration flow (create_user):
        Router → hash_password() → db.py stores the resulting hash.

    Login flow (authentication):
        db.py (get_user_by_email) → verify_password() → grants or denies access.

    This file never touches the database, and db.py never touches cryptography.
    Each module has a single responsibility: one owns the math, the other owns
    the data. This separation means you can swap bcrypt for argon2 (or any future
    algorithm) without modifying a single line in the persistence layer.
"""

import bcrypt


def hash_password(plain: str) -> str:
    """Convert a plaintext password into a bcrypt hash safe for storage."""
    # gensalt() generates a random salt each call — two users with the same
    # password will still get different hashes, preventing rainbow-table attacks.
    # bcrypt operates on bytes, so we encode to utf-8 first and decode back to str for DB storage.
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """
    Compare a plaintext password against the stored bcrypt hash.
    bcrypt hashing is one-way — you cannot reverse the hash back to plaintext.
    checkpw re-hashes the input with the same salt (embedded in the hash) and
    compares the results in constant time to prevent timing attacks.
    """
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))

"""Small passwordless reviewer authentication primitives."""

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone


TOKEN_LIFETIME_MINUTES = 20
EMAIL_LIMITS = ((15, 3), (24 * 60, 10))
SOURCE_LIMITS = ((15, 20), (24 * 60, 100))


class RateLimitError(RuntimeError):
    def __init__(self, retry_after=900):
        super().__init__("Too many sign-in requests")
        self.retry_after = retry_after


def normalize_email(value):
    email = str(value or "").strip().casefold()
    if not email or "@" not in email or email.startswith("@") or email.endswith("@"):
        raise ValueError("A valid email address is required")
    return email


def token_hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _private_key(secret, value):
    return hmac.new(secret.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).hexdigest()


def enforce_login_rate_limits(conn, email, source, secret, now=None):
    now = now or datetime.now(timezone.utc)
    email_key = _private_key(secret, normalize_email(email))
    source_key = _private_key(secret, str(source or "unknown"))
    conn.execute("BEGIN IMMEDIATE")
    conn.execute("DELETE FROM reviewer_auth_attempts WHERE created_at<?",
                 ((now - timedelta(hours=48)).isoformat(),))
    for key_column, key, limits in (
        ("email_key", email_key, EMAIL_LIMITS),
        ("source_key", source_key, SOURCE_LIMITS),
    ):
        for minutes, maximum in limits:
            count = conn.execute(
                f"SELECT COUNT(*) FROM reviewer_auth_attempts WHERE {key_column}=? AND created_at>=?",
                (key, (now - timedelta(minutes=minutes)).isoformat()),
            ).fetchone()[0]
            if count >= maximum:
                conn.rollback()
                raise RateLimitError(minutes * 60)
    conn.execute(
        "INSERT INTO reviewer_auth_attempts(email_key,source_key,outcome,created_at) "
        "VALUES (?,?,?,?)", (email_key, source_key, "accepted", now.isoformat())
    )
    conn.commit()


def invalidate_login_token(conn, raw_token, now=None):
    now = now or datetime.now(timezone.utc)
    conn.execute("UPDATE reviewer_login_tokens SET used_at=? WHERE token_hash=? AND used_at IS NULL",
                 (now.isoformat(), token_hash(raw_token)))
    conn.commit()


def supersede_login_tokens(conn, raw_token, email, now=None):
    now = now or datetime.now(timezone.utc)
    conn.execute("BEGIN IMMEDIATE")
    conn.execute(
        "UPDATE reviewer_login_tokens SET used_at=? WHERE normalized_email=? "
        "AND token_hash!=? AND used_at IS NULL",
        (now.isoformat(), normalize_email(email), token_hash(raw_token)),
    )
    conn.commit()


def reviewer_has_identity_data(conn, reviewer_id):
    reviewer = conn.execute(
        "SELECT display_name FROM community_reviewers WHERE id=?", (reviewer_id,)
    ).fetchone()
    if reviewer and reviewer[0]:
        return True
    for table, column in (("stop_review_assignments", "reviewer_id"),
                          ("stop_observations", "reviewer_id"),
                          ("community_stewardships", "reviewer_id")):
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        if exists and conn.execute(
            f"SELECT 1 FROM {table} WHERE {column}=? LIMIT 1", (reviewer_id,)
        ).fetchone():
            return True
    return False


def issue_login_token(conn, current_reviewer_id, email, now=None):
    normalized = normalize_email(email)
    now = now or datetime.now(timezone.utc)
    owner = conn.execute(
        "SELECT id FROM community_reviewers WHERE email=? "
        "AND email_verified_at IS NOT NULL", (normalized,)
    ).fetchone()
    if owner and owner[0] != current_reviewer_id:
        if reviewer_has_identity_data(conn, current_reviewer_id):
            target, action = current_reviewer_id, "conflict"
        else:
            target, action = owner[0], "login"
    elif owner:
        target, action = owner[0], "login"
    else:
        target, action = current_reviewer_id, "claim"
    raw = secrets.token_urlsafe(32)
    conn.execute(
        "INSERT INTO reviewer_login_tokens "
        "(reviewer_id,normalized_email,token_hash,action,expires_at) VALUES (?,?,?,?,?)",
        (target, normalized, token_hash(raw), action,
         (now + timedelta(minutes=TOKEN_LIFETIME_MINUTES)).isoformat()),
    )
    conn.commit()
    return raw


def consume_login_token(conn, raw_token, now=None):
    now = now or datetime.now(timezone.utc)
    conn.execute("BEGIN IMMEDIATE")
    row = conn.execute(
        "SELECT id,reviewer_id,normalized_email,action,expires_at,used_at "
        "FROM reviewer_login_tokens WHERE token_hash=?", (token_hash(raw_token),)
    ).fetchone()
    if not row or row[5] is not None:
        conn.rollback()
        raise ValueError("This sign-in link is invalid or has already been used")
    expires = datetime.fromisoformat(row[4])
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires <= now:
        conn.rollback()
        raise ValueError("This sign-in link has expired")
    if row[3] == "conflict":
        conn.execute("UPDATE reviewer_login_tokens SET used_at=? WHERE id=?",
                     (now.isoformat(), row[0]))
        conn.commit()
        raise PermissionError("This email belongs to another reviewer profile; accounts were not merged")
    if row[3] == "claim":
        owner = conn.execute(
            "SELECT id FROM community_reviewers WHERE email=? "
            "AND email_verified_at IS NOT NULL AND id!=?", (row[2], row[1])
        ).fetchone()
        if owner:
            conn.execute("UPDATE reviewer_login_tokens SET used_at=? WHERE id=?",
                         (now.isoformat(), row[0]))
            conn.commit()
            raise PermissionError("This email belongs to another reviewer profile")
        conn.execute(
            "UPDATE community_reviewers SET email=?,email_verified_at=?,claimed_at=? WHERE id=?",
            (row[2], now.isoformat(), now.isoformat(), row[1]),
        )
    conn.execute("UPDATE reviewer_login_tokens SET used_at=? WHERE id=?",
                 (now.isoformat(), row[0]))
    conn.commit()
    return row[1]

"""Local owner MFA, revocable sessions and confirmation data, never approval.

Cryptographic primitives are imported only for explicit MFA use. This module
neither imports synthetic providers nor issues recognition writer capabilities.
"""

from dataclasses import dataclass
import hashlib
import os
import secrets

from . import administration as a
from . import administration_schema as schema
from .rules import canonical, digest
from .trust import load


SESSION_SECONDS = 8 * 60 * 60
RECENT_SECONDS = 10 * 60
PRIMARY_SECONDS = SESSION_SECONDS + RECENT_SECONDS
ACTIONS = frozenset(("approve", "correct", "recover", "activate", "deactivate", "suspend", "clear_stop", "mfa_admin"))
OPERATION_ACTIONS = frozenset(("approve", "correct", "recover"))


@dataclass(frozen=True)
class AdminIdentity:
    actor_id: int
    installation_id: str
    generation: int


def _hash_key(value):
    return hashlib.sha256(value.encode()).hexdigest()


def _deny(conn, code, now, actor=None, status=403):
    a._audit(conn, "administration_denied", actor, now, dict(code=code))
    conn.commit()  # Persist throttles/revocation even though the request fails.
    raise a.AdminError(code, status)


def _owner(conn, target, binding, now):
    latest = conn.execute("SELECT body_json,body_sha256 FROM recognition_admin_audit ORDER BY sequence DESC LIMIT 1").fetchone()
    if latest:
        body = load(latest[0])
        a.need(digest(body) == latest[1] and a.timestamp(now) >= a.timestamp(body["at_utc"]), "administrative_clock_rollback", 503)
    from src.review.admin_dashboard import owner_access
    row = target.execute("SELECT reviewer_key FROM community_reviewers WHERE id=?", (binding["owner_id"],)).fetchone()
    allowed, _ = owner_access(target, binding["owner_id"], row[0] if row else None)
    if not allowed:
        a._invalidate(conn)
        _deny(conn, "recognition_owner_required", now)
    meta = target.execute(f"SELECT auth_epoch FROM {schema.TARGET_TABLE}").fetchone()
    return row[0], meta[0]


def _primary(conn, target, binding, token, now, *, recent=False):
    key, epoch = _owner(conn, target, binding, now)
    hashed = a.token_hash(token)
    row = conn.execute("SELECT * FROM recognition_admin_primary WHERE token_hash=?", (hashed,)).fetchone()
    t = a.timestamp(now)
    if not (row and not row["revoked"] and row["actor"] == binding["owner_id"]
            and row["key_hash"] == _hash_key(key) and row["auth_epoch"] == epoch
            and row["generation"] == binding["generation"] and row["created"] <= t < row["expires"]):
        if row:
            conn.execute("UPDATE recognition_admin_primary SET revoked=1 WHERE token_hash=?", (hashed,))
            conn.execute("UPDATE recognition_admin_sessions SET revoked=1 WHERE primary_hash=?", (hashed,))
        _deny(conn, "primary_authentication_required", now, status=401)
    if recent and t - row["created"] >= RECENT_SECONDS:
        _deny(conn, "recent_primary_authentication_required", now, row["actor"], 401)
    return row


def record_primary_authentication(config, *, actor_id, reviewer_key, now):
    """Trusted login hook after consume_login_token; never exposed as an HTTP API."""
    with a.transaction(config) as (conn, target, binding):
        key, epoch = _owner(conn, target, binding, now)
        a.need(type(actor_id) is int and actor_id == binding["owner_id"] and reviewer_key == key, "recognition_owner_required")
        raw = secrets.token_urlsafe(32)
        t = a.timestamp(now)
        conn.execute("INSERT INTO recognition_admin_primary VALUES(?,?,?,?,?,?,?,0)",
            (a.token_hash(raw), actor_id, _hash_key(key), epoch, binding["generation"], t, t + PRIMARY_SECONDS))
        a._audit(conn, "owner_primary_authenticated", actor_id, now)
        return raw


def invalidate_primary(config, token, *, now):
    if not token:
        return
    # Logout must work even if the target was replaced or is unavailable.
    with a.connect(config.control, write=True) as conn:
        conn.execute("BEGIN IMMEDIATE")
        schema.check_control(conn)
        hashed = a.token_hash(token)
        conn.execute("UPDATE recognition_admin_primary SET revoked=1 WHERE token_hash=?", (hashed,))
        conn.execute("UPDATE recognition_admin_sessions SET revoked=1 WHERE primary_hash=?", (hashed,))
        a._audit(conn, "administrative_logout", None, now)
        conn.commit()


def get_admin_identity(config, primary_token, *, now):
    with a.transaction(config) as (conn, target, binding):
        row = _primary(conn, target, binding, primary_token, now)
        return AdminIdentity(row["actor"], binding["installation_id"], binding["generation"])


def _cipher(config):
    from cryptography.fernet import Fernet
    path = config.key_file
    a.need(path.is_file() and not path.is_symlink(), "host_mfa_key_unavailable", 503)
    if os.name != "nt":
        a.need(path.stat().st_mode & 0o077 == 0, "host_mfa_key_permissions", 503)
    try:
        return Fernet(path.read_bytes().strip())
    except (ValueError, TypeError):
        raise a.AdminError("host_mfa_key_invalid", 503) from None


def _totp(seed):
    from cryptography.hazmat.primitives.twofactor.totp import TOTP
    from cryptography.hazmat.primitives.hashes import SHA1
    return TOTP(seed, 6, SHA1(), 30)


def begin_enrollment(config, primary_token, *, now):
    """Return provisioning URI ONCE during deliberate setup, never after enrollment."""
    import base64
    with a.transaction(config) as (conn, target, binding):
        primary = _primary(conn, target, binding, primary_token, now, recent=True)
        row = conn.execute("SELECT * FROM recognition_admin_mfa WHERE actor=?", (primary["actor"],)).fetchone()
        t = a.timestamp(now)
        a.need(row["state"] == "UNENROLLED" or (row["state"] == "PENDING" and row["pending_until"] <= t), "mfa_already_enrolled_or_pending")
        seed = secrets.token_bytes(20)
        body = dict(actor=primary["actor"], installation_id=binding["installation_id"], seed=base64.b64encode(seed).decode())
        encrypted = _cipher(config).encrypt(canonical(body).encode()).decode()
        conn.execute("UPDATE recognition_admin_mfa SET seed_ciphertext=?,state='PENDING',pending_primary=?,pending_until=?,last_counter=-1 WHERE actor=?",
                     (encrypted, primary["token_hash"], t + RECENT_SECONDS, primary["actor"]))
        a._audit(conn, "mfa_enrollment_begun", primary["actor"], now)
        return _totp(seed).get_provisioning_uri("owner-" + str(primary["actor"]), "DMV Bus Stops")


def _code(conn, config, binding, row, code, now):
    from cryptography.fernet import InvalidToken
    from cryptography.hazmat.primitives.twofactor import InvalidToken as InvalidOTP
    import base64
    t = a.timestamp(now)
    limit = conn.execute("SELECT * FROM recognition_admin_attempts WHERE actor=?", (row["actor"],)).fetchone()
    if limit and t < limit["window_start"] + 900 and limit["failures"] >= 5:
        _deny(conn, "mfa_rate_limited", now, row["actor"], 429)
    try:
        body = load(_cipher(config).decrypt(row["seed_ciphertext"].encode()).decode())
        a.need(body["actor"] == row["actor"] and body["installation_id"] == binding["installation_id"], "mfa_seed_binding_failure", 503)
        totp = _totp(base64.b64decode(body["seed"], validate=True))
    except (InvalidToken, ValueError, TypeError, KeyError):
        raise a.AdminError("mfa_seed_unavailable", 503) from None
    counter = None
    if type(code) is str and len(code) == 6 and code.isascii() and code.isdigit():
        for candidate in (t // 30 - 1, t // 30, t // 30 + 1):
            try:
                totp.verify(code.encode(), candidate * 30)
                if candidate > row["last_counter"]:
                    counter = candidate
            except InvalidOTP:
                pass
    if counter is None:
        start = limit["window_start"] if limit and t < limit["window_start"] + 900 else t
        failures = limit["failures"] + 1 if limit and start == limit["window_start"] else 1
        conn.execute("INSERT INTO recognition_admin_attempts VALUES(?,?,?) ON CONFLICT(actor) DO UPDATE SET window_start=excluded.window_start,failures=excluded.failures",
                     (row["actor"], start, failures))
        _deny(conn, "invalid_or_replayed_totp", now, row["actor"], 401)
    conn.execute("UPDATE recognition_admin_mfa SET last_counter=? WHERE actor=?", (counter, row["actor"]))


def finish_enrollment(config, primary_token, code, *, now):
    with a.transaction(config) as (conn, target, binding):
        primary = _primary(conn, target, binding, primary_token, now, recent=True)
        row = conn.execute("SELECT * FROM recognition_admin_mfa WHERE actor=?", (primary["actor"],)).fetchone()
        a.need(row["state"] == "PENDING" and row["pending_primary"] == primary["token_hash"]
               and a.timestamp(now) < row["pending_until"], "pending_enrollment_required")
        _code(conn, config, binding, row, code, now)
        conn.execute("UPDATE recognition_admin_mfa SET state='ENROLLED',pending_primary=NULL,pending_until=NULL WHERE actor=?", (primary["actor"],))
        a._audit(conn, "mfa_enrollment_completed", primary["actor"], now)


def open_admin_session(config, primary_token, code, *, now):
    with a.transaction(config) as (conn, target, binding):
        primary = _primary(conn, target, binding, primary_token, now, recent=True)
        mfa = conn.execute("SELECT * FROM recognition_admin_mfa WHERE actor=?", (primary["actor"],)).fetchone()
        a.need(mfa["state"] == "ENROLLED", "mfa_enrollment_required", 401)
        _code(conn, config, binding, mfa, code, now)
        raw = secrets.token_urlsafe(32)
        t = a.timestamp(now)
        conn.execute("INSERT INTO recognition_admin_sessions VALUES(?,?,?,?,?,?,?,?,0)",
            (a.token_hash(raw), primary["token_hash"], primary["actor"], binding["generation"], primary["auth_epoch"], mfa["epoch"], t, t + SESSION_SECONDS))
        a._audit(conn, "administrative_session_opened", primary["actor"], now)
        return raw


def _session(conn, target, binding, token, now, *, recent=False):
    hashed = a.token_hash(token)
    return _session_hash(conn, target, binding, hashed, now, recent=recent)


def _session_hash(conn, target, binding, hashed, now, *, recent=False):
    """Internal persisted-session check for trusted approval continuation only."""
    row = conn.execute("SELECT * FROM recognition_admin_sessions WHERE token_hash=?", (hashed,)).fetchone()
    if not row:
        _deny(conn, "administrative_session_required", now, status=401)
    key, epoch = _owner(conn, target, binding, now)
    primary = conn.execute("SELECT * FROM recognition_admin_primary WHERE token_hash=?", (row["primary_hash"],)).fetchone()
    mfa = conn.execute("SELECT * FROM recognition_admin_mfa WHERE actor=?", (row["actor"],)).fetchone()
    t = a.timestamp(now)
    if not (not row["revoked"] and row["actor"] == binding["owner_id"] and row["generation"] == binding["generation"]
            and row["auth_epoch"] == epoch and row["created"] <= t < row["expires"] and primary
            and not primary["revoked"] and primary["key_hash"] == _hash_key(key) and primary["auth_epoch"] == epoch
            and primary["created"] <= t < primary["expires"] and mfa["state"] == "ENROLLED" and mfa["epoch"] == row["mfa_epoch"]):
        conn.execute("UPDATE recognition_admin_sessions SET revoked=1 WHERE token_hash=?", (hashed,))
        _deny(conn, "administrative_session_expired_or_revoked", now, row["actor"], 401)
    if recent and t - primary["created"] >= RECENT_SECONDS:
        _deny(conn, "recent_primary_authentication_required", now, row["actor"], 401)
    return row, mfa


def require_recognition_admin(config, session_token, *, now):
    with a.transaction(config) as (conn, target, binding):
        row, _ = _session(conn, target, binding, session_token, now)
        return AdminIdentity(row["actor"], binding["installation_id"], binding["generation"])


def _operation(target, operation_id):
    from .operations import get_operation
    from .events import get_event
    a.need(type(operation_id) is str and 1 <= len(operation_id) <= 128, "operation_required")
    op = get_operation(target, operation_id)
    event = get_event(target, op["envelope"]["event_id"])
    return digest(op["envelope"]), digest(dict(decisions=op["decisions"], executions=op["executions"], event_state=event["state"]))


def create_step_up(config, session_token, code, *, action, operation_id=None, now):
    a.need(type(action) is str and action in ACTIONS and (operation_id is not None if action in OPERATION_ACTIONS else operation_id is None), "invalid_step_up_scope")
    with a.transaction(config) as (conn, target, binding):
        row, mfa = _session(conn, target, binding, session_token, now)
        operation_sha, state_sha = _scoped_operation(conn, target, operation_id, action) if operation_id else (None, None)
        _code(conn, config, binding, mfa, code, now)
        raw = secrets.token_urlsafe(32)
        expires = min(a.timestamp(now) + RECENT_SECONDS, row["expires"])
        conn.execute("INSERT INTO recognition_admin_stepups VALUES(?,?,?,?,?,?,?,?)", (a.token_hash(raw), row["token_hash"], action, operation_id, operation_sha, state_sha, binding["generation"], expires))
        a._audit(conn, "administrative_step_up", row["actor"], now, dict(action=action, operation_id=operation_id, operation_sha256=operation_sha))
        return raw


def _step(conn, target, binding, session, token, action, operation_id, now):
    row = conn.execute("SELECT * FROM recognition_admin_stepups WHERE token_hash=?", (a.token_hash(token),)).fetchone()
    a.need(row is not None and row["session_hash"] == session["token_hash"] and row["action"] == action
           and row["operation_id"] == operation_id and row["generation"] == binding["generation"]
           and a.timestamp(now) < row["expires"], "recent_step_up_required", 401)
    if operation_id:
        a.need(_scoped_operation(conn, target, operation_id, action) == (row["operation_sha256"], row["state_sha256"]), "operation_changed")
    return row


def _scoped_operation(control, target, operation_id, action):
    if action == "recover":
        from .production_receipts import recovery_binding
        binding = recovery_binding(control, target, operation_id)
        if binding is not None:
            return binding
    return _operation(target, operation_id)


def require_recent_step_up(config, session_token, step_token, *, action, operation_id=None, now):
    with a.transaction(config) as (conn, target, binding):
        session, _ = _session(conn, target, binding, session_token, now)
        _step(conn, target, binding, session, step_token, action, operation_id, now)
        return AdminIdentity(session["actor"], binding["installation_id"], binding["generation"])


def begin_operation_confirmation(config, session_token, step_token, *, operation_id, now):
    with a.transaction(config) as (conn, target, binding):
        session, _ = _session(conn, target, binding, session_token, now)
        step = _step(conn, target, binding, session, step_token, "approve", operation_id, now)
        raw = secrets.token_urlsafe(32)
        conn.execute("INSERT INTO recognition_admin_confirmations VALUES(?,?,?,?,?,?,?,?,0)",
            (a.token_hash(raw), session["token_hash"], session["actor"], operation_id, step["operation_sha256"], step["state_sha256"], binding["generation"], step["expires"]))
        a._audit(conn, "operation_confirmation_begun", session["actor"], now, dict(operation_id=operation_id, operation_sha256=step["operation_sha256"]))
        return raw


def consume_operation_confirmation(config, session_token, confirmation_token, *, operation_id, operation_sha256, now):
    """Consumes confirmation DATA only. No decision/approval/writer is invoked."""
    with a.transaction(config) as (conn, target, binding):
        session, _ = _session(conn, target, binding, session_token, now)
        row = conn.execute("SELECT * FROM recognition_admin_confirmations WHERE token_hash=?", (a.token_hash(confirmation_token),)).fetchone()
        a.need(row is not None and not row["used"] and row["session_hash"] == session["token_hash"]
               and row["actor"] == session["actor"] and row["generation"] == binding["generation"]
               and row["operation_id"] == operation_id and row["operation_sha256"] == operation_sha256
               and a.timestamp(now) < row["expires"], "invalid_or_consumed_confirmation")
        if _operation(target, operation_id) != (row["operation_sha256"], row["state_sha256"]):
            conn.execute("UPDATE recognition_admin_confirmations SET used=1 WHERE token_hash=?", (row["token_hash"],))
            _deny(conn, "operation_changed", now, session["actor"])
        conn.execute("UPDATE recognition_admin_confirmations SET used=1 WHERE token_hash=? AND used=0", (row["token_hash"],))
        body = dict(actor_id=session["actor"], operation_id=operation_id, operation_sha256=operation_sha256,
                    generation=binding["generation"], confirmed_at_utc=now, confirmation_sha256=row["token_hash"])
        a._audit(conn, "operation_confirmation_consumed", session["actor"], now, body)
        return body

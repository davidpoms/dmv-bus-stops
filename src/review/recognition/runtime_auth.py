"""Profile-scoped owner authentication only. No production admission adapter.

Login-token consumption remains in the existing login flow. Neither a runtime
observation nor a profile digest is a login credential. Clocks are read after
locks; the optional `now` argument only preserves the existing route interface.
"""

from . import administration as a, admin_auth as auth, runtime_validation as v
from . import runtime_profile_schema as r
from . import runtime_scope_validation as scope_validation


def _parts(context):
    return scope_validation._parts(context)


def _scope(control, scope, kind, proof, now):
    row = control.execute(f'SELECT * FROM {r.AUTH} WHERE token_kind=? AND token_hash=?',
                          (kind, proof['token_hash'])).fetchone()
    if not (row is not None and row['token_kind'] == kind and row['token_hash'] == proof['token_hash']
            and row['profile_sha256'] == scope['profile_sha256'] and row['created_at'] == proof['created']
            and proof['actor'] == scope['owner_id'] and proof['generation'] == scope['generation']):
        table = 'recognition_admin_primary' if kind == 'primary' else 'recognition_admin_sessions'
        control.execute(f'UPDATE {table} SET revoked=1 WHERE token_hash=?', (proof['token_hash'],))
        if kind == 'primary':
            control.execute('UPDATE recognition_admin_sessions SET revoked=1 WHERE primary_hash=?', (proof['token_hash'],))
        auth._deny(control, 'runtime_authentication_scope_required', now, scope['owner_id'], 401)


def _primary(context, token, now, *, recent=False):
    a.need(type(context) is v.RuntimeValidationContext, 'runtime_context_invalid', 503)
    return scope_validation._primary(context, token, now, recent=recent)


def _insert_scope(context, kind, token, now):
    control, _, _, scope = _parts(context)
    control.execute(f'INSERT INTO {r.AUTH} VALUES(?,?,?,?)',
        (kind, a.token_hash(token), scope['profile_sha256'], a.timestamp(now)))
    a._audit(control, 'runtime_authentication_scoped', scope['owner_id'], now,
             dict(token_kind=kind, token_hash=a.token_hash(token), profile_sha256=scope['profile_sha256'],
                  generation=scope['generation'], installation_id=scope['installation_id'], target_id=scope['target_id']))


def record_primary_authentication(config, *, actor_id, reviewer_key, now=None):
    """Existing trusted login hook only, after successful login-token consumption."""
    with v.authentication_transaction(config) as context:
        control, target, binding, _ = _parts(context)
        fresh = v._utc_now()
        raw = auth._record_primary(control, target, binding, actor_id=actor_id, reviewer_key=reviewer_key, now=fresh)
        _insert_scope(context, 'primary', raw, fresh)
        _primary(context, raw, fresh)
    return raw


def get_admin_identity(config, primary_token, *, now=None):
    with v.authentication_transaction(config) as context:
        primary = _primary(context, primary_token, v._utc_now())
        _, _, binding, _ = _parts(context)
        result = auth.AdminIdentity(primary['actor'], binding['installation_id'], binding['generation'])
    return result


def begin_enrollment(config, primary_token, *, now=None):
    with v.authentication_transaction(config) as context:
        fresh = v._utc_now()
        _primary(context, primary_token, fresh, recent=True)
        control, target, binding, _ = _parts(context)
        result = auth._begin_enrollment(control, target, binding, config, primary_token, now=fresh)
    return result


def finish_enrollment(config, primary_token, code, *, now=None):
    with v.authentication_transaction(config) as context:
        fresh = v._utc_now()
        _primary(context, primary_token, fresh, recent=True)
        control, target, binding, _ = _parts(context)
        auth._finish_enrollment(control, target, binding, config, primary_token, code, now=fresh)


def open_admin_session(config, primary_token, code, *, now=None):
    with v.authentication_transaction(config) as context:
        fresh = v._utc_now()
        _primary(context, primary_token, fresh, recent=True)
        control, target, binding, _ = _parts(context)
        raw = auth._open_admin_session(control, target, binding, config, primary_token, code, now=fresh)
        _insert_scope(context, 'session', raw, fresh)
        _session(context, raw, primary_token, fresh)
    return raw


def _session(context, session_token, primary_token, now):
    a.need(type(context) is v.RuntimeValidationContext, 'runtime_context_invalid', 503)
    return scope_validation._session(context, session_token, primary_token, now)


def require_recognition_admin(config, session_token, *, primary_token, now=None):
    """Both opaque browser references are required; no caller-supplied scope."""
    with v.authentication_transaction(config) as context:
        session = _session(context, session_token, primary_token, v._utc_now())
        _, _, binding, _ = _parts(context)
        result = auth.AdminIdentity(session['actor'], binding['installation_id'], binding['generation'])
    return result


invalidate_primary = auth.invalidate_primary  # Revocation works even if target is unavailable.

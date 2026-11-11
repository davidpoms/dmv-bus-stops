"""4b-0: live read-only scope validation, not a transaction or capability.

The authentication and proposal owners have separate explicit registrations.
The proposal owner cannot relabel itself as a 3a context or issue authentication.
Private Python reflection/host compromise is outside the existing integrity model.
"""

from types import MappingProxyType
from weakref import WeakKeyDictionary

from . import administration as a, admin_auth as auth, runtime_validation as v
from .trust import load


_views = WeakKeyDictionary()
_proposal_views = WeakKeyDictionary()
_approval_views = WeakKeyDictionary()
_claim_views = WeakKeyDictionary()
_activated_views = WeakKeyDictionary()
_consent_views = WeakKeyDictionary()
_issuance_views = WeakKeyDictionary()
_coordinator_views = WeakKeyDictionary()
_metadata_views = WeakKeyDictionary()
_finalization_views = WeakKeyDictionary()


def _parts(context):
    """Internal guarded handles, never part of the public read-view result."""
    a.need(type(context) is v.RuntimeValidationContext, 'runtime_context_invalid', 503)
    data = v._contexts.get(context)
    a.need(data is not None, 'runtime_context_invalid', 503)
    v._context_data(context, data['control'], data['target'])
    state = v._states[context]
    a.need(v._snapshot(state.config, state.control, state.target, v._utc_now()) == data['snapshot'],
           'runtime_validation_changed', 503)
    control, target = data['control'], data['target']
    binding = load(control.execute('SELECT body_json FROM recognition_admin_bindings ORDER BY generation DESC LIMIT 1').fetchone()[0])
    return control, target, binding, data['snapshot']


def _mfa(control, scope):
    row = control.execute('SELECT state,epoch FROM recognition_admin_mfa WHERE actor=?',
                          (scope['owner_id'],)).fetchone()
    a.need(row is not None and row['state'] == 'ENROLLED' and type(row['epoch']) is int
           and row['epoch'] > 0, 'runtime_contract_mfa_not_enrolled')
    return row['epoch']


def _view_parts(view):
    a.need(type(view) is RuntimeReadView, 'runtime_context_invalid', 503)
    if view in _finalization_views:
        from . import runtime_finalization as owner
        context, epoch = _finalization_views[view]
        parts = owner._read_parts(context)
        a.need(_mfa(parts[0], parts[3]) == epoch, 'runtime_validation_changed', 503)
        return context, parts, epoch
    if view in _metadata_views:
        from . import runtime_target_entry_owner as metadata
        context, epoch = _metadata_views[view]
        parts = metadata._read_parts(context)
        a.need(_mfa(parts[0], parts[3]) == epoch, 'runtime_validation_changed', 503)
        return context, parts, epoch
    if view in _coordinator_views:
        from . import runtime_execution_coordinator as coordinator
        context, epoch = _coordinator_views[view]
        parts = coordinator._read_parts(context)
        a.need(_mfa(parts[0], parts[3]) == epoch, 'runtime_validation_changed', 503)
        return context, parts, epoch
    if view in _issuance_views:
        from . import runtime_activation_authority_issuance as issuance
        context, epoch = _issuance_views[view]
        parts = issuance._read_parts(context)
        a.need(_mfa(parts[0], parts[3]) == epoch, 'runtime_validation_changed', 503)
        return context, parts, epoch
    if view in _consent_views:
        from . import runtime_authority_consent_transaction as consent
        context, epoch = _consent_views[view]
        parts = consent._read_parts(context)
        a.need(_mfa(parts[0], parts[3]) == epoch, 'runtime_validation_changed', 503)
        return context, parts, epoch
    if view in _activated_views:
        from . import runtime_activated_owner as activated
        context, epoch = _activated_views[view]
        parts = activated._read_parts(context)
        a.need(_mfa(parts[0], parts[3]) == epoch, 'runtime_validation_changed', 503)
        return context, parts, epoch
    if view in _claim_views:
        from . import runtime_claim_validation as claim
        context, epoch = _claim_views[view]
        parts = claim._read_parts(context)
        a.need(_mfa(parts[0], parts[3]) == epoch, 'runtime_validation_changed', 503)
        return context, parts, epoch
    if view in _approval_views:
        from . import runtime_approval_transaction as approval
        context, epoch = _approval_views[view]
        parts = approval._read_parts(context)
        a.need(_mfa(parts[0], parts[3]) == epoch, 'runtime_validation_changed', 503)
        return context, parts, epoch
    if view in _proposal_views:
        from . import runtime_proposal_transaction as proposal
        context, epoch = _proposal_views[view]
        parts = proposal._read_parts(context)
        a.need(_mfa(parts[0], parts[3]) == epoch, 'runtime_validation_changed', 503)
        return context, parts, epoch
    entry = _views.get(view)
    a.need(entry is not None, 'runtime_context_invalid', 503)
    context, epoch = entry
    parts = _parts(context)
    a.need(_mfa(parts[0], parts[3]) == epoch, 'runtime_validation_changed', 503)
    return context, parts, epoch


class RuntimeReadView:
    """No SQL, handles, tokens, lifecycle operations or detached authentication."""

    __slots__ = ('__weakref__',)

    def __new__(cls):
        raise TypeError('runtime_read_view_requires_live_context')

    def snapshot(self):
        _, (_, _, _, scope), epoch = _view_parts(self)
        return MappingProxyType(dict(scope, mfa_epoch=epoch))

    def validate_session(self, session_token, *, primary_token):
        _view_parts(self)
        session = _session(self, session_token, primary_token, v._utc_now())
        # Return data, never the underlying Row/connection or supplied tokens.
        return MappingProxyType(dict(actor_id=session['actor'], generation=session['generation']))


def read_view(context):
    """Borrow the current 3a transaction; never opens or owns a transaction."""
    control, _, _, scope = _parts(context)
    epoch = _mfa(control, scope)
    view = object.__new__(RuntimeReadView)
    _views[view] = (context, epoch)
    return view


def _register_proposal_view(context):
    """Explicit adapter, no supplied provider/handles/scope or 3a registration."""
    from . import runtime_proposal_transaction as proposal
    control, _, _, current = proposal._read_parts(context)
    view = object.__new__(RuntimeReadView)
    _proposal_views[view] = (context, _mfa(control, current))
    return view


def _kernel_parts(source):
    if type(source) is RuntimeReadView:
        return _view_parts(source)[1]
    return _parts(source)  # Still exclusively the exact registered 3a type.


def _register_approval_view(context):
    from . import runtime_approval_transaction as approval
    control, _, _, current = approval._read_parts(context)
    view = object.__new__(RuntimeReadView)
    _approval_views[view] = (context, _mfa(control, current))
    return view


def _register_claim_view(context):
    """Distinct validation-only owner; never accepts a proposal/3a context."""
    from . import runtime_claim_validation as claim
    control, _, _, current = claim._read_parts(context)
    view = object.__new__(RuntimeReadView)
    _claim_views[view] = (context, _mfa(control, current))
    return view


def _register_activated_view(context):
    from . import runtime_activated_owner as activated
    control, _, _, current = activated._read_parts(context)
    view = object.__new__(RuntimeReadView)
    _activated_views[view] = (context, _mfa(control, current))
    return view


def _validate_expiry(expires, code):
    """Pure shared validation; no registration, transaction or authority."""
    v.enrollment._integer(expires)
    a.need(code in {'primary_authentication_required', 'recent_primary_authentication_required',
                    'administrative_session_expired_or_revoked'}, 'runtime_auth_expiry_invalid', 503)


def _register_consent_view(context):
    from . import runtime_authority_consent_transaction as consent
    control, _, _, current = consent._read_parts(context)
    view = object.__new__(RuntimeReadView)
    _consent_views[view] = (context, _mfa(control, current))
    return view


def _register_issuance_view(context):
    from . import runtime_activation_authority_issuance as issuance
    control, _, _, current = issuance._read_parts(context)
    view = object.__new__(RuntimeReadView)
    _issuance_views[view] = (context, _mfa(control, current))
    return view


def _register_coordinator_view(context):
    from . import runtime_execution_coordinator as coordinator
    control, _, _, current = coordinator._read_parts(context)
    view = object.__new__(RuntimeReadView)
    _coordinator_views[view] = (context, _mfa(control, current))
    return view


def _register_metadata_view(context):
    from . import runtime_target_entry_owner as metadata
    control, _, _, current = metadata._read_parts(context)
    view = object.__new__(RuntimeReadView)
    _metadata_views[view] = (context, _mfa(control, current))
    return view


def _register_finalization_view(context):
    from . import runtime_finalization as owner
    control, _, _, current = owner._read_parts(context)
    view = object.__new__(RuntimeReadView)
    _finalization_views[view] = (context, _mfa(control, current))
    return view


def _require_expiry(source, expires, code):
    if type(source) is RuntimeReadView:
        context, _, _ = _view_parts(source)
        if source in _finalization_views:
            from . import runtime_finalization as owner
            owner._require_auth_expiry(context, expires, code)
            return
        if source in _metadata_views:
            from . import runtime_target_entry_owner as metadata
            metadata._require_auth_expiry(context, expires, code)
            return
        if source in _coordinator_views:
            from . import runtime_execution_coordinator as coordinator
            coordinator._require_auth_expiry(context, expires, code)
            return
        if source in _issuance_views:
            from . import runtime_activation_authority_issuance as issuance
            issuance._require_auth_expiry(context, expires, code)
            return
        if source in _consent_views:
            from . import runtime_authority_consent_transaction as consent
            consent._require_auth_expiry(context, expires, code)
            return
        if source in _activated_views:
            from . import runtime_activated_owner as activated
            activated._require_auth_expiry(context, expires, code)
            return
        if source in _claim_views:
            from . import runtime_claim_validation as claim
            claim._require_auth_expiry(context, expires, code)
            return
        if source in _approval_views:
            from . import runtime_approval_transaction as approval
            approval._require_auth_expiry(context, expires, code)
            return
        if source in _proposal_views:
            from . import runtime_proposal_transaction as proposal
            proposal._require_auth_expiry(context, expires, code)
            return
    else:
        context = source
    v._require_auth_expiry(context, expires, code)


def _primary(source, token, now, *, recent=False):
    from . import runtime_auth as ra
    control, target, binding, current = _kernel_parts(source)
    primary = auth._primary(control, target, binding, token, now, recent=recent)
    ra._scope(control, current, 'primary', primary, now)
    _require_expiry(source, primary['expires'], 'primary_authentication_required')
    if recent:
        _require_expiry(source, primary['created'] + auth.RECENT_SECONDS, 'recent_primary_authentication_required')
    return primary


def _session(context, session_token, primary_token, now):
    """Shared existing-record validator, including existing denial reductions.

    Success performs reads only. Existing authentication rejection may revoke
    credentials/audit denial under the owning 3a manager's unchanged rules.
    No credentials are issued and authentication never escapes its transaction.
    """
    from . import runtime_auth as ra
    primary = _primary(context, primary_token, now)
    control, target, binding, scope = _kernel_parts(context)
    session, _ = auth._session(control, target, binding, session_token, now)
    ra._scope(control, scope, 'session', session, now)
    if not (session['primary_hash'] == primary['token_hash']
            and session['actor'] == primary['actor'] == scope['owner_id']
            and session['generation'] == primary['generation'] == scope['generation']):
        auth._deny(control, 'administrative_browser_session_mismatch', now, scope['owner_id'])
    _require_expiry(context, session['expires'], 'administrative_session_expired_or_revoked')
    return session


def _contract_parts(context):
    """Private 4a adapter: both accepted forms resolve to the same live manager."""
    if type(context) is RuntimeReadView:
        _, parts, epoch = _view_parts(context)
    else:
        parts = _parts(context)
        epoch = _mfa(parts[0], parts[3])
    control, _, binding, scope = parts
    return control, binding, scope, epoch

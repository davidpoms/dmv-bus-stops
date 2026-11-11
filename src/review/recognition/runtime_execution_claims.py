"""One exact control-side claim, never target writes, consumption or execution."""

from dataclasses import asdict
from datetime import timedelta
import os
import sqlite3
import threading
import time
from uuid import uuid4
from weakref import WeakKeyDictionary

from . import administration as a, administration_schema
from . import runtime_admission_validation as shared, runtime_claim_validation as owner
from . import runtime_execution_admission as admission, runtime_execution_claim_schema as schema
from . import runtime_operation_contract as contract, runtime_validation as runtime
from .rules import canonical, digest
from .trust import identity, load, require, utc


_receipts = WeakKeyDictionary()
_NS = 1_000_000_000


class _Clock:
    """Private paired UTC/monotonic samples; no caller clock/skew/lifetime input."""

    def __init__(self):
        self.previous = None
        self.issued = None
        self.read()

    def read(self):
        before = time.monotonic_ns()
        text = runtime._utc_now()
        epoch = a.timestamp(text)
        after = time.monotonic_ns()
        require(type(before) is int and type(after) is int and 0 <= before <= after,
                'runtime_claim_clock_anomaly')
        if self.previous is not None:
            old_before, old_epoch, old_after = self.previous
            delta = epoch-old_epoch
            # UTC is quantized to whole seconds. Possible elapsed durations must
            # overlap its quantization interval; there is no configurable grace.
            require(before >= old_after and delta >= 0
                    and before-old_after < (delta+1)*_NS
                    and after-old_before > (delta-1)*_NS, 'runtime_claim_clock_anomaly')
        self.previous = (before, epoch, after)
        return text, epoch


class ClaimCommitOutcome(a.AdminError):
    """No handle was published. Inspect durable state; NEVER automatically retry."""

    def __init__(self, body, committed):
        self.control_committed = committed  # True or None (uncertain).
        self.inspection_reference = canonical(body)  # Hashes/observations, no raw credentials.
        super().__init__('runtime_claim_committed_without_handle' if committed is True
                         else 'runtime_claim_commit_outcome_unknown', 503)


class ExecutionClaim:
    """Process/thread-local acquisition receipt, NOT a writer/handoff capability.

    No adoption, renewal, consumption, execution or authentication API exists.
    Inspection/export remains historical data, never proof of current authority.
    """

    __slots__ = ('__weakref__',)

    def __new__(cls):
        raise TypeError('runtime_claim_requires_acquisition')

    @property
    def canonical_json(self):
        return _receipt(self)['json']

    @property
    def sha256(self):
        return _receipt(self)['sha256']

    @property
    def snapshot(self):
        return admission._freeze(load(self.canonical_json))

    @property
    def inspection_reference(self):
        # Deliberately historical, even after expiry. This cannot recreate a
        # receipt or authorize a retry, authentication, consumption or execution.
        return _receipt(self, historical=True)['json']

    def __reduce_ex__(self, protocol):
        raise TypeError('runtime_claim_cannot_be_restored')


def _live_time(pending):
    body, clock = pending['body'], pending['clock']
    _, now = clock.read()
    issued, expires = a.timestamp(body['issued_at_utc']), a.timestamp(body['expires_at_utc'])
    require(expires == issued+300 and issued <= now < expires, 'runtime_claim_expired_or_invalid_time')
    require(clock.issued is not None and clock.previous[2]-clock.issued[0] < 300*_NS,
            'runtime_claim_expired_or_invalid_time')
    return now


def _receipt(receipt, *, historical=False):
    value = _receipts.get(receipt) if type(receipt) is ExecutionClaim else None
    require(value is not None and value['pid'] == os.getpid()
            and value['thread'] is threading.current_thread(), 'runtime_claim_receipt_invalid')
    if not historical:
        _live_time(value)
    return value


def _rows(control, table):
    # Table names come exclusively from the already exact-validated schema.
    return sorted((tuple(row) for row in control.execute('SELECT * FROM "'+table+'"')), key=repr)


def _protected(control):
    return {name:_rows(control,name) for name, in control.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        if name not in (schema.CLAIMS,schema.HISTORY,'recognition_admin_audit')}


def _body(observed, original_sha256, issued):
    return dict(format=schema.FORMAT,claim_id=str(uuid4()),operation_id=observed['proposal']['operation_id'],
        operation_sha256=digest(observed['proposal']),proposal_sha256=digest(observed['proposal']),
        proposal_reference=observed['reference'],acknowledgement_sha256=observed['reference']['acknowledgement_sha256'],
        approval_id=observed['approval']['approval_id'],approval_sha256=observed['approval_sha256'],
        approval_history_sha256=observed['approval_history_sha256'],runtime_scope=observed['runtime_scope'],
        authentication=observed['authentication'],dependency_snapshot_sha256=digest(observed['dependency_snapshot']),
        target_snapshot=observed['target_snapshot'],target_snapshot_sha256=digest(observed['target_snapshot']),
        admission_sha256=original_sha256,emergency_stop_snapshot_sha256=digest(observed['emergency_stop_snapshot']),
        issued_at_utc=issued,expires_at_utc=(utc(issued)+timedelta(seconds=300)).strftime('%Y-%m-%dT%H:%M:%SZ'),
        state='ISSUED')


def _insert(state):
    """Fixed, manager-private three INSERTs. No public writer/callback seam."""
    state.check()
    pending = state.pending_claim
    require(pending is not None and not pending['inserted'], 'runtime_claim_insert_invalid')
    state.claim_write = True
    state.control.set_authorizer(state.control_authorizer)
    try:
        state.control.execute('INSERT INTO '+schema.CLAIMS+' VALUES(?,?,?,?,?,?,?,?,?)', pending['row'])
        state.control.execute('INSERT INTO '+schema.HISTORY+' VALUES(?,?,?,?,?,?,?)', pending['event_row'])
        body, event = pending['body'], pending['event']
        a._audit(state.control,'runtime_execution_claim_issued',body['runtime_scope']['owner_id'],body['issued_at_utc'],
            dict(claim_id=body['claim_id'],claim_sha256=digest(body),event_sequence=1,event_sha256=digest(event)))
    finally:
        state.claim_write = False
        # Never allow cached INSERT authorization to escape its fixed phase.
        state.control.set_authorizer(state.control_authorizer)
    require(state.control.total_changes == state.control_changes+3, 'runtime_claim_write_integrity')
    state.control_changes += 3
    pending['inserted'] = True


def _final_check(state):
    pending = state.pending_claim
    require(pending is not None and pending['inserted'], 'runtime_claim_insert_incomplete')
    # Reuses ALL authoritative readers and original snapshot comparison under
    # these SAME reservations, after the complete claim/genesis/audit graph.
    shared.validate(pending['view'],pending['snapshot'],pending['session'],primary_token=pending['primary']).sha256
    require(_protected(state.control) == pending['protected'], 'runtime_claim_protected_state_changed')
    require(_rows(state.control,schema.CLAIMS) == pending['claims']
            and _rows(state.control,schema.HISTORY) == pending['history'], 'runtime_claim_write_integrity')
    require([tuple(row) for row in state.control.execute(
        'SELECT * FROM recognition_admin_audit WHERE sequence>? ORDER BY sequence',(state.audit_sequence,))]
        == [pending['audit']], 'runtime_claim_audit_integrity')
    a._audit_head(state.control)
    _live_time(pending)


def acquire(config, snapshot, session_token, *, primary_token):
    """Acquire exactly once; no automatic retry, consumption or target write.

    Requires a genuine 4d-0 object, current existing credentials and the installed
    control schema. The returned receipt is published only after commit/cleanup.
    """
    original = admission._data(snapshot)
    require(config == original['config'], 'runtime_admission_configuration_mismatch')
    clock, state, pending = _Clock(), None, None
    try:
        with owner.validation_transaction(config) as context:
            state = owner._state(context)
            require(state.control.execute("SELECT 1 FROM sqlite_master WHERE name=?",(schema.CLAIMS,)).fetchone(),
                    'runtime_claim_schema_not_installed')
            view = shared.claim_read_view(context)
            observed = load(shared.validate(view,snapshot,session_token,primary_token=primary_token).canonical_json)
            issued, epoch = clock.read()
            require(epoch >= a.timestamp(observed['checked_at_utc']), 'runtime_claim_clock_anomaly')
            body = _body(observed,original['sha256'],issued)
            contract._json(body)
            clock.issued = clock.previous
            expires = a.timestamp(body['expires_at_utc'])
            require(state.auth_expiries and all(deadline >= expires for deadline,_ in state.auth_expiries),
                    'runtime_claim_insufficient_authentication_lifetime')
            head = a._audit_head(state.control)
            sequence = (head['sequence'] if head else 0)+1
            event = dict(format=schema.EVENT_FORMAT,claim_id=body['claim_id'],claim_sha256=digest(body),sequence=1,
                previous_sha256=None,state='ISSUED',reason='Exact approved runtime admission acquired',at_utc=issued)
            row = (body['claim_id'],body['operation_id'],canonical(body),digest(body),body['runtime_scope']['generation'],
                body['runtime_scope']['runtime_profile_sha256'],epoch,expires,sequence)
            event_row = (body['claim_id'],1,'ISSUED',epoch,canonical(event),digest(event),sequence)
            audit = dict(action='runtime_execution_claim_issued',actor=body['runtime_scope']['owner_id'],at_utc=issued,
                subject=dict(claim_id=body['claim_id'],claim_sha256=digest(body),event_sequence=1,event_sha256=digest(event)),
                previous_sha256=head['body_sha256'] if head else None)
            pending = dict(body=body,clock=clock,view=view,snapshot=snapshot,session=session_token,primary=primary_token,
                row=row,event=event,event_row=event_row,audit=(sequence,canonical(audit),digest(audit)),inserted=False,
                protected=_protected(state.control),claims=sorted(_rows(state.control,schema.CLAIMS)+[row],key=repr),
                history=sorted(_rows(state.control,schema.HISTORY)+[event_row],key=repr))
            state.pending_claim = pending  # After this point ALL failures roll back, including denials.
            _live_time(pending)
            try:
                _insert(state)
            except sqlite3.IntegrityError:
                exists = state.control.execute('SELECT claim_id FROM '+schema.CLAIMS+' WHERE operation_id=?',
                    (body['operation_id'],)).fetchone()
                duplicate = exists is not None and exists['claim_id'] != body['claim_id']
                raise a.AdminError('runtime_claim_already_acquired' if duplicate else 'runtime_claim_insert_rejected') from None
            # The owner invokes final T2/row/clock checks and commits control
            # while target is still reserved. Nothing authoritative escapes here.
    except BaseException:
        if pending is not None and state is not None and state.commit_attempted:
            raise ClaimCommitOutcome(pending['body'],state.control_committed) from None
        raise
    if state.control_committed is not True or not state.control_resolved or state.active:
        raise ClaimCommitOutcome(pending['body'],None)
    try:
        _live_time(pending)
    except BaseException:
        raise ClaimCommitOutcome(pending['body'],True) from None
    receipt = object.__new__(ExecutionClaim)
    _receipts[receipt] = dict(pid=os.getpid(),thread=threading.current_thread(),body=pending['body'],clock=clock,
                            json=canonical(pending['body']),sha256=digest(pending['body']))
    return receipt


def inspect_acquisition(config, inspection_reference):
    """Trusted deployment-side, SQLite mode=ro data inspection; NEVER retry/adopt.

    An absent read snapshot cannot exclude another pending writer: return
    ABSENT_AT_SNAPSHOT, never permission to retry. Recovery-required/unreadable
    storage returns UNKNOWN without attempting repairs or opening target.
    """
    require(type(config) is a.LocalAdministration, 'local_administration_required')
    config.paths()
    require(type(inspection_reference) is str and len(inspection_reference.encode('utf-8')) <= 65536,
            'runtime_claim_inspection_reference_invalid')
    expected = schema._body(inspection_reference,digest(load(inspection_reference)))
    require(type(expected) is dict and expected.get('format') == schema.FORMAT,
            'runtime_claim_inspection_reference_invalid')
    identity(expected.get('claim_id'))
    identity(expected.get('operation_id'))
    result = dict(claim_id=expected['claim_id'],operation_id=expected['operation_id'],retry_authorized=False)
    try:
        from . import runtime_challenges
        with a.connect(config.control) as control:
            control.execute('BEGIN')
            administration_schema.check_control(control)
            a._audit_head(control)
            binding = runtime_challenges._deployment_binding(control)
            require(asdict(a.target_identity(control)) == binding['control_identity'], 'control_identity_mismatch')
            require(str(config.target.resolve()) == binding['target']['observation']['database'], 'target_path_mismatch')
            # integrity_check may initialize TEMP. Keep the exact control-schema
            # connection isolation invariant intact by using a separate RO handle.
            with a.connect(config.control) as integrity:
                require([row[0] for row in integrity.execute('PRAGMA integrity_check')] == ['ok'],
                        'runtime_claim_inspection_integrity')
            rows = control.execute('SELECT * FROM '+schema.CLAIMS+' WHERE claim_id=? OR operation_id=?',
                (expected['claim_id'],expected['operation_id'])).fetchall()
            if not rows:
                return dict(result,status='ABSENT_AT_SNAPSHOT')
            exact = (len(rows) == 1 and rows[0]['claim_id'] == expected['claim_id']
                and rows[0]['operation_id'] == expected['operation_id']
                and rows[0]['body_json'] == inspection_reference and rows[0]['body_sha256'] == digest(expected))
            return dict(result,status='PRESENT_EXACT' if exact else 'PRESENT_CONFLICT')
    except (ValueError,OSError,sqlite3.Error,KeyError,TypeError):
        return dict(result,status='UNKNOWN')

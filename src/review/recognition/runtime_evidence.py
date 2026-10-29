"""Read-only worker evidence; private-log provenance requires operator review.

No signature, nonce possession, or hostname string authenticates a runtime here.
Only the explicitly armed WSGI hook emits evidence for later local approval.
"""

from dataclasses import asdict
from datetime import datetime, timezone
import os
from pathlib import Path
import sys
import threading

from . import administration as a, administration_schema as schema
from . import runtime_profile_schema as r
from .runtime_challenges import _deployment_binding
from .rules import canonical, digest
from .trust import identity


MARKER = 'RECOGNITION_RUNTIME_EVIDENCE'
FORMAT = 'recognition-runtime-observation-v1'
CHANNEL = 'operator-reviewed-private-wsgi-log-v1'


def _challenge(control, challenge_id, expected_sha256, now):
    schema.check_control(control)
    a._audit_head(control)
    binding = _deployment_binding(control)
    row = control.execute(f'SELECT * FROM {r.CHALLENGES} WHERE challenge_id=?', (challenge_id,)).fetchone()
    a.need(row is not None, 'runtime_challenge_not_found')
    row = dict(row)
    # Validate stored CHECK semantics too: exact DDL does not prove an earlier
    # connection respected constraints. Reuse Slice 1's canonical SQL helpers.
    checks = [r.uuid(k) for k in ('challenge_id','installation_id','target_id')]
    checks += [r.sha(k) for k in ('source_binding_sha256','nonce_sha256','challenge_sha256')]
    checks += [r.integer(k,1,9223372036854775807) for k in ('source_generation','owner_id','audit_sequence')]
    checks += [r.integer('issued_at'),r.integer('expires_at'),r.text('operator',200),r.text('reason',2000),
               "format='recognition-runtime-enrollment-challenge-v1'", "role='runtime'", 'expires_at=issued_at+600']
    a.need(control.execute(f"SELECT 1 FROM {r.CHALLENGES} WHERE challenge_id=? AND COALESCE(({' AND '.join(checks)}),0)",
                           (challenge_id,)).fetchone(), 'runtime_challenge_constraint_failure')
    a.need(row['challenge_sha256'] == expected_sha256, 'runtime_challenge_digest_mismatch')
    a.need(not control.execute(f'SELECT 1 FROM {r.PROFILES} WHERE challenge_id=?', (challenge_id,)).fetchone(),
           'runtime_challenge_consumed')
    a.need(row['source_generation'] == binding['generation']
           and row['source_binding_sha256'] == digest(binding), 'runtime_challenge_stale')
    a.need(row['installation_id'] == binding['installation_id'] and row['target_id'] == binding['target_id']
           and row['owner_id'] == binding['owner_id'] and row['role'] == 'runtime', 'runtime_challenge_scope_mismatch')
    a.need(row['issued_at'] <= a.timestamp(now) < row['expires_at'], 'runtime_challenge_expired_or_not_yet_valid')
    a.need(binding['production_state'] == 'NOT_ACTIVATED', 'runtime_collection_requires_not_activated')
    if control.execute("SELECT 1 FROM sqlite_master WHERE name='recognition_local_activation'").fetchone():
        from .local_readiness import _state
        a.need(_state(control, binding)['state'] == 'NOT_ACTIVATED', 'runtime_collection_requires_not_activated')
    return row, binding


def _paths(target, control):
    for path in (target, control):
        a.need(isinstance(path, Path) and path.is_absolute(), 'explicit_runtime_paths_required')
    a.need(target.resolve() != control.resolve(), 'separate_control_store_required')


def _physical(value):
    a.need(type(value) is dict and set(value) == {'hostname','database','device','inode'}, 'runtime_identity_fields_invalid')
    a.need(type(value['hostname']) is str and value['hostname'].strip() and '\x00' not in value['hostname'],
           'runtime_hostname_invalid')
    a.need(type(value['database']) is str and '\x00' not in value['database'], 'runtime_path_invalid')
    path = Path(value['database'])
    a.need(path.is_absolute() and str(path.resolve()) == value['database'], 'runtime_path_invalid')
    a.need(type(value['device']) is int and type(value['inode']) is int, 'runtime_identity_integer_required')
    r._check_decimal(str(value['device']))
    r._check_decimal(str(value['inode']), inode=True)


def _observation(control, target, target_path, control_path, binding):
    schema.check_target(target)
    a.need(type(binding['target']) is dict and set(binding['target']) == {'observation','schema_sha256'},
           'runtime_target_fields_invalid')
    observed = a.observe_target(target)
    actual_control = asdict(a.target_identity(control))
    # Bound paths/inodes/schema remain strict. Host/device are independently
    # observed runtime evidence, not compared to deployment namespace values.
    for path, actual, bound in ((target_path, observed['observation'], binding['target']['observation']),
                               (control_path, actual_control, binding['control_identity'])):
        _physical(actual)
        _physical(bound)
        a.need(actual == asdict(a.target_identity(path)), 'runtime_identity_changed')
        a.need(actual['database'] == bound['database'] == str(path.resolve())
               and actual['inode'] == bound['inode'], 'runtime_path_or_inode_mismatch')
    a.need(observed['observation']['hostname'] == actual_control['hostname'], 'runtime_hostname_mismatch')
    a.need(observed['schema_sha256'] == binding['target']['schema_sha256'], 'runtime_schema_mismatch')
    r._check_sha(observed['schema_sha256'])
    metadata = target.execute(f'SELECT * FROM {schema.TARGET_TABLE}').fetchone()
    a.need(metadata is not None and all(metadata[k] == binding[k] for k in ('installation_id','target_id','owner_id')),
           'runtime_installation_target_mismatch')
    owner = target.execute('SELECT role,email_verified_at FROM community_reviewers WHERE id=?', (binding['owner_id'],)).fetchone()
    a.need(owner is not None and owner['role'] == 'owner' and owner['email_verified_at'], 'verified_project_owner_required')
    return observed, actual_control


def _collect(target_path, control_path, *, challenge_id, challenge_sha256, now):
    """Private read-only collector; only its WSGI hook supplies production input.

    Repeated collection is permitted, not consumption. Later enrollment MUST
    revalidate current state and independently establish private-log provenance.
    """
    _paths(target_path, control_path)
    identity(challenge_id)
    r._check_sha(challenge_sha256)
    a.timestamp(now)
    with a.connect(control_path) as control:
        control.execute('BEGIN')
        challenge, binding = _challenge(control, challenge_id, challenge_sha256, now)
        with a.connect(target_path) as target:
            target.execute('BEGIN')
            observed, actual_control = _observation(control, target, target_path, control_path, binding)
            # Independent snapshots detect generation, consumption and schema
            # changes that WAL readers could otherwise miss. This is evidence,
            # not a cross-database authorization/commit reservation.
            with a.connect(control_path) as fresh_control, a.connect(target_path) as fresh_target:
                fresh_control.execute('BEGIN')
                fresh_target.execute('BEGIN')
                fresh_challenge, fresh_binding = _challenge(fresh_control, challenge_id, challenge_sha256, now)
                a.need(fresh_binding == binding and fresh_challenge == challenge, 'runtime_collection_state_changed')
                a.need(_observation(fresh_control, fresh_target, target_path, control_path, binding)
                       == (observed, actual_control), 'runtime_identity_changed')
    payload = dict(format=FORMAT, role='runtime', installation_id=binding['installation_id'],
        target_id=binding['target_id'], owner_id=binding['owner_id'], source_generation=binding['generation'],
        source_binding_sha256=digest(binding), challenge_id=challenge_id, challenge_sha256=challenge_sha256,
        nonce_sha256=challenge['nonce_sha256'], challenge_expires_at=challenge['expires_at'], observed_at=a.timestamp(now),
        hostname=actual_control['hostname'], target_path=observed['observation']['database'],
        target_device=str(observed['observation']['device']), target_inode=str(observed['observation']['inode']),
        control_path=actual_control['database'], control_device=str(actual_control['device']),
        control_inode=str(actual_control['inode']), target_schema_sha256=observed['schema_sha256'],
        pid=os.getpid(), python_version=sys.version, python_executable=sys.executable,
        evidence_channel=CHANNEL, provenance='REQUIRES_OPERATOR_REVIEW')
    return dict(observation=payload, observation_sha256=digest(payload))


def _log_record(app, record):
    message = canonical(record)
    try:
        app.logger.warning('%s %s', MARKER, message)
    except Exception:
        # A failed private log sink supplies no evidence and must not interrupt
        # ordinary requests. Do not retry or expose a fallback through HTTP.
        pass


def register_runtime_evidence(app, target_path):
    """Once per PID/arm, on a real WSGI request; no routes or request inputs.

    Arming values and paths come ONLY from trusted application configuration.
    Do not put the nonce in configuration. Failures emit a fixed classification,
    never exception text, configuration contents or HTTP output.
    """
    from flask import request
    seen, lock = set(), threading.Lock()

    @app.before_request
    def collect_armed_runtime_evidence():
        challenge_id = app.config.get('RECOGNITION_RUNTIME_CHALLENGE_ID')
        challenge_sha256 = app.config.get('RECOGNITION_RUNTIME_CHALLENGE_SHA256')
        if not challenge_id and not challenge_sha256:
            return
        with lock:
            # Invalid configuration must not break requests or leak its values.
            arm = (os.getpid(), repr(challenge_id), repr(challenge_sha256))
            if arm in seen:
                return
            seen.add(arm)
            try:
                a.need(request.environ.get('wsgi.version') == (1, 0), 'wsgi_runtime_required')
                raw_control = app.config.get('RECOGNITION_ADMIN_CONTROL')
                a.need(type(raw_control) is str and raw_control, 'runtime_control_path_required')
                record = _collect(target_path(), Path(raw_control), challenge_id=challenge_id,
                    challenge_sha256=challenge_sha256,
                    now=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
                a.need(a.timestamp(datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
                       < record['observation']['challenge_expires_at'], 'runtime_challenge_expired')
            except Exception:
                _log_record(app, dict(status='REJECTED',
                    error='runtime_evidence_collection_failed', pid=os.getpid()))
                return
            _log_record(app, record)

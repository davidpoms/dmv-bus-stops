"""Explicit disposable-only approvals for synthetic fixtures, never production.

The allowlist models an independently reviewed approval store and revocation.
No verifier approves an unknown object, target, or production environment.
"""

from dataclasses import asdict
import json
from pathlib import Path

from src.review.recognition import authorization as auth, permanent, live_first_looks as live
from src.review.recognition import permanent_schema, live_first_look_schema
from src.review.recognition.report_connection import report_connection
from src.review.recognition.rules import digest
from src.review.recognition.authority import DisposableWorkspace as _Workspace

_workspaces = []


class DisposableWorkspace(_Workspace):
    def __init__(self):
        super().__init__()
        _workspaces.append(self)

    def cleanup(self):
        _workspaces.remove(self)
        super().cleanup()


def workspace_for(database):
    path = Path(auth.target_identity(database).database)
    return next(w for w in _workspaces if path.is_relative_to(Path(w.name)))


class FixtureAuthority:
    def approve(self, database, **binding):
        workspace = workspace_for(database)
        self.authority = workspace.authority
        self.approved = workspace.approved
        return workspace.approve(database, **binding)


def approval(database, **binding):
    authority = FixtureAuthority()
    return dict(authorization=authority.approve(database, **binding), authority=authority.authority)


def finalize(database, manifest, **kwargs):
    return permanent.finalize(database, manifest, **{
        **approval(database, **auth.manifest_binding(manifest)), **kwargs})


def migrate_private(database, *, apply=False, **kwargs):
    if apply:
        kwargs = {**approval(database, **auth.migration_binding('private_recognition', permanent_schema.definitions())), **kwargs}
    return permanent_schema.migrate(database, apply=apply, **kwargs)


def migrate_live(database, *, apply=False, **kwargs):
    if apply:
        kwargs = {**approval(database, **auth.migration_binding('first_look', live_first_look_schema.OBJECTS)), **kwargs}
    return live_first_look_schema.migrate(database, apply=apply, **kwargs)


def install_private(conn, **kwargs):
    return permanent_schema.install(conn, **{
        **approval(conn, **auth.migration_binding('private_recognition', permanent_schema.definitions())), **kwargs})


def enqueue(conn, assignment_id, **kwargs):
    config = kwargs.get('configuration')
    if conn is not None and config is not None:
        kwargs = {**approval(conn, **auth.admission_binding(asdict(config))), **kwargs}
    return live.enqueue(conn, assignment_id, **kwargs)


def sealing_binding(conn, config, fact, decision):
    prepared = permanent._prepare(conn, 'first_look', decision['inputs'], decision['evaluation_at_utc'], decision['reference'])
    baseline = live._sealed_baseline(conn, decision['historical_operation_id'], config)
    manifest = {**prepared, 'format': 'live-first-look-operation-v1', 'configuration': config,
                'rule': live._rule(config), 'rule_sha256': digest(live._rule(config)),
                'candidates': [c for c in prepared['candidates'] if c['physical_stop_id'] == fact['physical_stop_id']],
                'finality_decision': decision, 'historical_baseline': baseline, 'trigger_completion': fact}
    return auth.manifest_binding(manifest)


def seal_pending(conn, assignment_id, **kwargs):
    if conn is None:
        return live.seal_pending(conn, assignment_id, **kwargs)
    config = json.loads(conn.execute('SELECT configuration_json FROM recognition_first_look_pending WHERE assignment_id=?',
                                     (assignment_id,)).fetchone()[0])
    stored = dict(conn.execute('SELECT * FROM recognition_completions WHERE assignment_id=?', (assignment_id,)).fetchone())
    fact = {key: stored[key] for key in ('assignment_id', 'observation_id', 'reviewer_id', 'physical_stop_id',
            'completed_at_utc', 'original_completed_at', 'timestamp_provenance')}
    binding = dict(family='first_look', permission='issuance', action='seal_pending',
                   policy_sha256=config['policy_sha256'], operation_sha256=digest('deferred-fixture'),
                   population_sha256=digest('deferred-fixture'), reference='synthetic-deferred')
    guard = kwargs.get('finality_guard')
    if guard is not None:
        try:
            with report_connection(conn):
                decision = guard(conn, {'configuration': config, 'completion': fact,
                    'ledger_sequence': max((f['ledger_sequence'] for f in permanent._ledger(conn)), default=0),
                    'identity_sha256': digest(permanent._identity(conn))})
            if decision is not None:
                binding = sealing_binding(conn, config, fact, decision)
        except Exception:
            pass  # Approve only a defer attempt; real writer still exercises failure.
    delivery = approval(conn, **live.delivery_binding(conn, assignment_id))
    return live.seal_pending(conn, assignment_id, **{**approval(conn, **binding),
        'delivery_authorization': delivery['authorization'], **kwargs})


def record_retryable_failure(conn, assignment_id, error, **kwargs):
    if conn is not None:
        binding = {**live.delivery_binding(conn, assignment_id), 'action': 'record_retryable_failure'}
        kwargs = {**approval(conn, **binding), **kwargs}
    return live.record_retryable_failure(conn, assignment_id, error, **kwargs)


def append_discrepancy(database, **kwargs):
    body = {key: kwargs[key] for key in ('physical_stop_id', 'evidence', 'review_reference', 'reviewed_at_utc')}
    return permanent.append_discrepancy(database, **{**approval(database, family='first_look', permission='issuance',
        action='append_discrepancy', operation_sha256=digest(body), policy_sha256=digest(permanent.DEFINITIONS['first_look']),
        population_sha256=None, reference=body['review_reference']), **kwargs})

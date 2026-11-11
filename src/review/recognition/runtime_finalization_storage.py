"""R22 explicit disposable bootstrap and journal persistence kernels.

These bootstrap entry points remain disposable/pre-enrollment only. Enrolled
owner installation uses runtime_finalization_schema_upgrade and the protected
schema/profile transition; fingerprints/manifests are never silently repaired.
"""
from . import administration as a, administration_schema as base, authorization
from . import runtime_decision_outcome_journal_schema as journal
from .rules import canonical, digest
from .trust import require


def _disposable(conn, approval, authority, side):
    require(approval is not None and approval.environment == 'disposable',
            'finalization_disposable_only')
    authorization.verify_migration(conn, 'runtime_finalization_'+side,
                                   journal.definitions(side), approval, authority)


def install_target(conn, *, approval, authority):
    """Explicit fresh-target installer, before installation identity is frozen."""
    require(conn.in_transaction, 'finalization_install_transaction')
    _disposable(conn, approval, authority, 'target')
    require(not conn.execute("SELECT 1 FROM sqlite_master WHERE name='recognition_local_installation'").fetchone(),
            'finalization_install_before_enrollment')
    _install(conn, 'target')


def install_control(conn, *, approval, authority):
    require(conn.in_transaction, 'finalization_install_transaction')
    _disposable(conn, approval, authority, 'control')
    base.check_control(conn)
    require(not conn.execute("SELECT 1 FROM sqlite_master WHERE name='recognition_runtime_profiles'").fetchone(),
            'finalization_install_before_enrollment')
    _install(conn, 'control')
    base.check_control(conn)


def _install(conn, side):
    conn.execute('SAVEPOINT finalization_bootstrap')
    try:
        for name, sql in journal.definitions(side).items():
            if not conn.execute('SELECT 1 FROM sqlite_master WHERE name=?', (name,)).fetchone():
                conn.execute(sql)
        journal.check_schema(conn, side)
        conn.execute('RELEASE finalization_bootstrap')
    except BaseException:
        conn.execute('ROLLBACK TO finalization_bootstrap')
        conn.execute('RELEASE finalization_bootstrap')
        raise


def _insert(conn, table, row):
    require(table in (journal.DECISIONS, journal.HISTORY, journal.WITNESSES), 'finalization_journal_table')
    conn.execute('INSERT INTO '+table+' ('+','.join(row)+') VALUES ('+','.join('?' for _ in row)+')', tuple(row.values()))


def _decision_row(decision):
    src = decision['authority']; ref = src['operation_reference']; scope = src['runtime_target']
    return dict(authority_id=src['authority_id'], authority_sha256=digest(src),
        installation_id=scope['installation_id'], target_id=scope['target_id'],
        operation_id=ref['operation_id'], operation_sha256=ref['operation_sha256'],
        writer_manifest_sha256=ref['writer_manifest_sha256'], recorded_at=a.timestamp(decision['recorded_at_utc']),
        body_json=canonical(decision), body_sha256=digest(decision))


def _event_row(event):
    return dict(authority_id=event['authority_id'], authority_sha256=event['authority_sha256'],
        sequence=event['sequence'], state=event['state'], at=a.timestamp(event['at_utc']),
        previous_sha256=event['previous_sha256'], body_json=canonical(event), body_sha256=digest(event))


def _witness_row(witness):
    row = _decision_row(witness['decision'])
    row.update(recorded_at=a.timestamp(witness['recorded_at_utc']), body_json=canonical(witness),
               body_sha256=digest(witness), pending_sha256=digest(witness['pending']),
               effect_evidence_sha256=witness['effect_evidence_sha256'])
    return row

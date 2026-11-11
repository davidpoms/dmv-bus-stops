"""Private R22 fixed-family mutation and actual-record proof. No authority API.

The caller must already own an entitled target transaction. These helpers never
open a database, authorize a caller, commit, construct a capability or run DDL.
"""

from . import permanent
from .rules import canonical, digest
from .trust import require


TABLES = (
    'recognition_private_rules', 'recognition_private_operations',
    'recognition_first_look_claims', 'recognition_geography_scope_identities',
    'recognition_geography_snapshots', 'recognition_geography_members',
    'recognition_geography_awards', 'recognition_geography_witnesses',
)


def _rows(conn, table):
    require(table in TABLES, 'finalization_effect_table')
    columns = [row[1] for row in conn.execute('PRAGMA table_info('+table+')')]
    return sorted((dict(zip(columns, tuple(row))) for row in conn.execute('SELECT * FROM '+table)),
                  key=canonical)


def _family_snapshot(conn):
    return {table: _rows(conn, table) for table in TABLES}


def _expected(manifest, sealed_at, *, existing_rule):
    """Derive complete expected inserted rows independently of the SQL writer."""
    m = manifest
    rule = m['rule']; op = digest(m)
    tuples = {table: [] for table in TABLES}
    if not existing_rule:
        tuples[TABLES[0]] = [(rule['rule_key'], m['family'], canonical(rule), digest(rule))]
    tuples[TABLES[1]] = [(op, rule['rule_key'], canonical(m), op, m['authorization_reference'], sealed_at)]
    if m['family'] == 'first_look':
        tuples[TABLES[2]] = [(c['physical_stop_id'], c['reviewer_id'], c['assignment_id'], op,
                              c['completed_at_utc'], canonical(c), digest(c)) for c in m['candidates']]
    else:
        require(m['family'] == 'geography_steward', 'finalization_family')
        for item in m['report']['scopes']:
            scope = item['snapshot_scope']
            tuples[TABLES[3]].append(tuple(scope[k] for k in
                ('scope_key', 'dimension', 'canonical_geography_id', 'display_label')))
            tuples[TABLES[4]].append((digest(scope), scope['scope_key'], op, canonical(scope), digest(scope)))
            tuples[TABLES[5]].extend((digest(scope), n) for n in item['member_physical_stop_ids'])
        for c in m['candidates']:
            tuples[TABLES[6]].append((digest(c), c['reviewer_id'], c['scope_key'], c['tier_key'],
                c['snapshot_id'], op, c['earned_at_utc'], c['numerator'], c['denominator'],
                c['percentage'], c['size_band'], canonical(c), digest(c)))
            tuples[TABLES[7]].extend((digest(c), w['assignment_id']) for w in c['witnesses'])
    return tuples


def _verify_delta(conn, manifest, before):
    require(set(before) == set(TABLES), 'finalization_effect_baseline')
    op = permanent._operation(conn, digest(manifest))
    require(op == manifest, 'finalization_manifest_changed')
    operation = conn.execute('SELECT sealed_at_utc FROM recognition_private_operations WHERE operation_id=?',
                             (digest(manifest),)).fetchone()
    require(operation is not None, 'finalization_operation_missing')
    existing_rule = any(r['rule_key'] == manifest['rule']['rule_key'] for r in before[TABLES[0]])
    expected = _expected(manifest, operation[0], existing_rule=existing_rule)
    actual = _family_snapshot(conn)
    for table in TABLES:
        columns = [r[1] for r in conn.execute('PRAGMA table_info('+table+')')]
        added = [dict(zip(columns, row)) for row in expected[table]]
        require(actual[table] == sorted(before[table]+added, key=canonical),
                'finalization_effect_delta_mismatch')
    permanent._verify_operation_records(conn, digest(manifest))
    require(not conn.execute('PRAGMA foreign_key_check').fetchone(), 'finalization_foreign_keys')
    return actual


def _evidence(conn, manifest, decision, pending):
    """Canonical full actual rows belonging to this operation, for reinspection."""
    op = digest(manifest)
    permanent._verify_operation_records(conn, op)
    all_rows = _family_snapshot(conn)
    rows = {table: [] for table in TABLES}
    rows[TABLES[0]] = [r for r in all_rows[TABLES[0]] if r['rule_key'] == manifest['rule']['rule_key']]
    for table in (TABLES[1], TABLES[2], TABLES[4], TABLES[6]):
        rows[table] = [r for r in all_rows[table] if r['operation_id'] == op]
    snapshots = {r['snapshot_id'] for r in rows[TABLES[4]]}
    scopes = {r['scope_key'] for r in rows[TABLES[4]]}
    awards = {r['award_id'] for r in rows[TABLES[6]]}
    rows[TABLES[3]] = [r for r in all_rows[TABLES[3]] if r['scope_key'] in scopes]
    rows[TABLES[5]] = [r for r in all_rows[TABLES[5]] if r['snapshot_id'] in snapshots]
    rows[TABLES[7]] = [r for r in all_rows[TABLES[7]] if r['award_id'] in awards]
    source = decision['authority']
    return dict(format='recognition-runtime-complete-family-effect-v1',
                authority_id=source['authority_id'], authority_sha256=digest(source),
                pending_sha256=digest(pending), manifest_sha256=op,
                runtime_target=source['runtime_target'], records=rows)


def _verify_witness_effect(conn, manifest, decision, pending, witness):
    """Actual record/witness binding. Owner separately proves committed snapshot."""
    from . import runtime_decision_outcome_journal_schema as journal
    journal.validate_witness(witness)
    require(witness['decision']==decision and witness['pending']==pending
            and decision['authority']['operation_reference']['writer_manifest_sha256']==digest(manifest),
            'finalization_witness_binding')
    require(digest(_evidence(conn,manifest,decision,pending))==witness['effect_evidence_sha256'],
            'finalization_committed_effect_mismatch')

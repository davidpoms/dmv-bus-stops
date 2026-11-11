"""R11-C ordered schema DATA verification. No installer or runtime authority.

Successor definitions are exact metadata reused by the explicit migration owner.
This module provides neither an installer nor any authority issuance selection.
"""

from . import administration as admin, administration_schema as base
from . import runtime_activation_authority_schema as authority
from . import runtime_execution_attempt_schema as attempts
from . import runtime_enrollment_transition_schema as transition
from . import runtime_execution_claim_schema as claims, runtime_profile_schema as profile
from .rules import canonical, digest
from .trust import fields, identity, load, require


MIGRATION = 'recognition-runtime-authority-lifetime-policies-v2'
ACTION = 'runtime_authority_lifetime_policy_schema_upgraded'
V2 = 'recognition-runtime-authority-lifetime-300s-v2'
SUBJECT = ('migration_id', 'previous_schema_sha256', 'installed_schema_sha256',
           'installation_id', 'generation', 'reason')


def successor_definitions():
    """Exact R10 successor metadata; never installed or selected by this module."""
    result = authority.definitions().copy()
    table = result[authority.AUTHORITIES]
    old_range = profile.integer('issued_at', 0, profile.MAX_TIME-120)
    require(table.count(old_range) == 1, 'lineage_original_definition_changed')
    table = table.replace(old_range, profile.integer('issued_at', 0, profile.MAX_TIME))
    old = 'CHECK(issued_at<expires_at AND expires_at<=issued_at+120)'
    require(table.count(old) == 1, 'lineage_original_definition_changed')
    policy = "json_extract(body_json,'$.lifetime_policy')"
    cases = ' OR '.join(
        f"({policy}='{name}' AND issued_at<={profile.MAX_TIME-seconds} AND expires_at<=issued_at+{seconds})"
        for name, seconds in ((authority.LIFETIME, 120), (V2, 300)))
    result[authority.AUTHORITIES] = table.replace(old,
        "CHECK(COALESCE(typeof(issued_at)='integer' AND typeof(expires_at)='integer' "
        f'AND issued_at<expires_at AND ({cases}),0))')
    name = authority.AUTHORITIES+'_scope_guard'
    old_policy = f"json_extract(NEW.body_json,'$.lifetime_policy')='{authority.LIFETIME}'"
    require(result[name].count(old_policy) == 1, 'lineage_original_definition_changed')
    # Preserve all existing scope predicates. SQL correlates original source
    # records; the authoritative historical reader must still verify their digests.
    cutover = (
        "(SELECT count(*) FROM recognition_admin_audit WHERE "
        f"json_extract(body_json,'$.action')='{ACTION}')=1 AND EXISTS("
        'SELECT 1 FROM recognition_admin_audit l, recognition_admin_audit st, '
        'recognition_admin_audit cf, recognition_admin_audit ca WHERE '
        f"json_extract(l.body_json,'$.action')='{ACTION}' AND "
        f"json_extract(l.body_json,'$.subject.migration_id')='{MIGRATION}' AND "
        "json_extract(l.body_json,'$.subject.installation_id')=NEW.installation_id AND "
        f"json_extract(st.body_json,'$.action')='{authority.STEP_ACTION}' AND "
        f"json_extract(cf.body_json,'$.action')='{authority.CONFIRM_ACTION}' AND "
        f"json_extract(ca.body_json,'$.action')='{authority.CONSUME_ACTION}' AND "
        "json_extract(cf.body_json,'$.subject.token_sha256')=NEW.confirmation_sha256 AND "
        "json_extract(ca.body_json,'$.subject.token_sha256')=NEW.confirmation_sha256 AND "
        "json_extract(st.body_json,'$.subject.subject_sha256')="
        "json_extract(cf.body_json,'$.subject.subject_sha256') AND "
        "json_extract(cf.body_json,'$.subject.step_artifact_sha256')="
        "json_extract(NEW.body_json,'$.producer_ceremony.step_artifact_sha256') AND "
        "json_extract(ca.body_json,'$.subject.artifact_sha256')="
        "json_extract(NEW.body_json,'$.producer_ceremony.confirmation_artifact_sha256') AND "
        'l.sequence<st.sequence AND st.sequence<cf.sequence AND cf.sequence<ca.sequence '
        'AND ca.sequence<NEW.audit_sequence AND '
        "json_extract(l.body_json,'$.at_utc')<=json_extract(NEW.body_json,'$.issued_at_utc'))")
    result[name] = result[name].replace(old_policy,
        f"({old_policy} OR (json_extract(NEW.body_json,'$.lifetime_policy')='{V2}' AND {cutover}))")
    return result


def present(conn):
    """Detect the typed cutover, including a mismatched action/known-ID claim."""
    return bool(conn.execute(
        "SELECT 1 FROM recognition_admin_audit WHERE json_extract(body_json,'$.action')=? "
        "OR json_extract(body_json,'$.subject.migration_id')=? LIMIT 1", (ACTION, MIGRATION)).fetchone())


def _normalized(objects):
    return {name: ' '.join(sql.split()) for name, sql in objects.items()}


def _scope(conn, row, migration_id):
    value = authority._record(row)
    subject = value['subject']; fields(subject, SUBJECT)
    require(subject['migration_id'] == migration_id, 'lineage_migration_identity')
    for key in ('previous_schema_sha256', 'installed_schema_sha256'):
        profile._check_sha(subject[key])
    identity(subject['installation_id'])
    profile._check_sha(row['body_sha256'])
    require(type(subject['generation']) is int and 1 <= subject['generation'] <= 2**63-1,
            'lineage_generation')
    authority._reason(subject['reason']); authority._reason(value['actor'])
    authority._time(value['at_utc'])
    binding = conn.execute('SELECT * FROM recognition_admin_bindings WHERE generation=?',
                           (subject['generation'],)).fetchone()
    require(binding is not None, 'lineage_binding_missing')
    body = load(binding['body_json'])
    require(canonical(body) == binding['body_json'] and digest(body) == binding['body_sha256']
            and body['installation_id'] == subject['installation_id']
            and type(body['generation']) is int
            and body['generation'] == subject['generation'], 'lineage_binding_scope')
    return value


def verify(conn):
    """Fresh exact edge verification; detached returned DATA is never authority.

    No callbacks, caller-defined schemas, caller-selected hashes, writes or cache.
    This kernel does not replace full control/row/current admission validation.
    """
    require(len(conn.execute('PRAGMA database_list').fetchall()) == 1,
            'isolated_admin_control_required')
    admin._audit_head(conn)
    actual = _normalized(dict(base._control_objects(conn)))
    from . import approval_schema, local_readiness
    baseline = base.definitions()
    baseline.update(approval_schema.definitions())
    baseline.update(local_readiness.definitions())
    baseline.update(profile.definitions()); baseline.update(claims.definitions())
    # R22 bootstrap is permitted only before runtime enrollment/claim anchoring.
    # Include its exact immutable definitions in the original root, never project
    # a later install out of history or accept an arbitrary package map.
    from . import runtime_decision_outcome_journal_schema as outcome
    from . import runtime_finalization_schema_upgrade as finalization
    later_journal=finalization.present(conn)
    if (outcome.DECISIONS in actual or outcome.HISTORY in actual) and not later_journal:
        baseline.update(outcome.definitions('control'))
    baseline = _normalized(baseline)
    packages = dict(A=(authority.MIGRATION, authority.ACTION, authority.definitions()),
                    T=(attempts.MIGRATION, attempts.ACTION, attempts.definitions()),
                    E=(transition.MIGRATION, transition.ACTION, transition.definitions()),
                    L=(MIGRATION, ACTION, successor_definitions()),
                    J=(finalization.MIGRATION, finalization.ACTION, finalization.definitions()))
    by_action = {v[1]: k for k, v in packages.items()}
    by_id = {v[0]: k for k, v in packages.items()}
    by_action[claims.ACTION] = 'root'
    by_id[claims.MIGRATION] = 'root'
    roots = authority._rows(conn, claims.ACTION)
    require(len(roots) == 1, 'lineage_claim_anchor')
    edges = {}
    for row in conn.execute('SELECT * FROM recognition_admin_audit ORDER BY sequence'):
        value = authority._record(row)
        subject = value['subject']
        action_key = by_action.get(value['action'])
        migration_id = subject.get('migration_id') if type(subject) is dict else None
        id_key = by_id.get(migration_id) if type(migration_id) is str else None
        if action_key is None and id_key is None:
            require(not (row['sequence'] > roots[0]['sequence'] and type(subject) is dict
                         and 'migration_id' in subject and 'previous_schema_sha256' in subject
                         and 'installed_schema_sha256' in subject), 'lineage_unknown_schema_edge')
            continue
        require(action_key is not None and action_key == id_key and action_key not in edges,
                'lineage_duplicate_or_unknown_edge')
        if action_key == 'root':
            continue  # Its exact shape/scope/hashes are independently checked below.
        edges[action_key] = dict(sequence=row['sequence'],
            audit=_scope(conn, row, packages[action_key][0]))
    require('A' in edges, 'lineage_authority_missing')
    root = _scope(conn, roots[0], claims.MIGRATION)
    require(root['subject']['installed_schema_sha256'] == digest(baseline)
            and root['subject']['previous_schema_sha256'] == digest({
                k: v for k, v in baseline.items() if k not in claims.definitions()})
            and roots[0]['sequence'] < edges['A']['sequence'], 'lineage_claim_anchor')
    state = dict(baseline)
    seen = set()
    for key, edge in sorted(edges.items(), key=lambda item: item[1]['sequence']):
        required = dict(A=set(), T={'A'}, E={'T'}, L={'A'}, J={'A','T','E','L'})[key]
        require(required <= seen, 'lineage_skipped_or_reordered_edge')
        edge['before'] = dict(state)
        definitions = _normalized(packages[key][2])
        if key == 'J':
            require(state.get(finalization.GUARD)==_normalized(transition.definitions())[finalization.GUARD],
                    'journal_original_guard_mismatch')
            require(not (set(definitions)-{finalization.GUARD}).intersection(state),'lineage_package_collision')
        elif key == 'L':
            original = _normalized(authority.definitions())
            require(all(state.get(n) == sql for n, sql in original.items()), 'lineage_original_schema')
            require(set(definitions) == set(original), 'lineage_successor_object_set')
        else:
            require(not set(state).intersection(definitions), 'lineage_package_collision')
        state.update(definitions)
        edge['after'] = dict(state)
        subject = edge['audit']['subject']
        require(subject['previous_schema_sha256'] == digest(edge['before'])
                and subject['installed_schema_sha256'] == digest(edge['after']),
                'lineage_edge_manifest_mismatch')
        seen.add(key)
    require(actual == state, 'lineage_current_schema_mismatch')
    return edges


def subject(conn, edge):
    edges = verify(conn)
    require(edge in edges, 'lineage_package_missing')
    return edges[edge]['audit']['subject']


def manifest_at(conn, edge, *, before=False, exclude=()):
    """Internal historical projection. Never used for current installer hashes."""
    edges = verify(conn)
    require(edge in edges, 'lineage_package_missing')
    # Existing readers exclude only their own known packages; no arbitrary map
    # is accepted and the complete lineage is verified before any exclusion.
    allowed = set(authority.definitions()) | set(attempts.definitions()) | set(transition.definitions()) | set(claims.definitions())
    omitted = set(exclude)
    require(omitted <= allowed, 'lineage_unknown_projection')
    objects = edges[edge]['before' if before else 'after']
    return digest({k: v for k, v in objects.items() if k not in omitted})

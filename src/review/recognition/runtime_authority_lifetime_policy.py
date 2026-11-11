"""Closed lifetime policy DATA and explicit inert control migration.

No policy adoption, issuance selection, runtime continuation or target mutation.
The original authority definitions remain available unchanged for lineage.
"""

from dataclasses import asdict

from . import administration as admin, administration_schema as base
from . import runtime_activation_authority_schema as authority
from . import runtime_schema_package_lineage as lineage
from . import runtime_execution_attempt_schema as attempts
from . import runtime_execution_claim_schema as claims
from . import runtime_operation_contract as operation
from .trust import load, require


MIGRATION = lineage.MIGRATION
ACTION = lineage.ACTION
STAGING = 'recognition_authority_lifetime_upgrade_staging'


def seconds(policy):
    """Resolve an immutable ID, never today's default or a numeric override."""
    require(type(policy) is str, 'runtime_authority_lifetime_policy')
    if policy == authority.LIFETIME:
        return 120
    if policy == lineage.V2:
        return 300
    require(False, 'runtime_authority_lifetime_policy')


def _quote(name):
    return '"'+name.replace('"', '""')+'"'


def _snapshot(conn):
    result = {}
    for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
        name = row[0]
        columns = [r['name'] for r in conn.execute('PRAGMA main.table_info('+_quote(name)+')')]
        result[name] = [tuple(r) for r in conn.execute(
            'SELECT * FROM '+_quote(name)+' ORDER BY '+','.join(map(_quote, columns)))]
    return result


def _rebuild(conn):
    """Private reserved DDL sequence. All validation/commit belongs to migrate()."""
    require(conn.in_transaction and conn.execute('PRAGMA foreign_keys').fetchone()[0] == 1,
            'lifetime_migration_transaction_required')
    require(len(conn.execute('PRAGMA database_list').fetchall()) == 1,
            'isolated_admin_control_required')
    incoming = {(authority.LIFECYCLE, 'authority_id', 'authority_id'),
                (attempts.ATTEMPTS, 'authority_id', 'authority_id'),
                (attempts.ATTEMPTS, 'authority_sha256', 'body_sha256')}
    for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'"):
        for fk in conn.execute('PRAGMA main.foreign_key_list('+_quote(row[0])+')'):
            if fk['table'] == authority.AUTHORITIES:
                require((row[0], fk['from'], fk['to']) in incoming
                        and fk['on_update'] == fk['on_delete'] == 'NO ACTION',
                        'lifetime_migration_unknown_reference')
    info = conn.execute('PRAGMA main.table_info('+authority.AUTHORITIES+')').fetchall()
    require(info and all(r['type'] in ('TEXT', 'INTEGER') for r in info),
            'lifetime_migration_column_types')
    names = ','.join(_quote(r['name']) for r in info)
    columns = ','.join(_quote(r['name'])+' '+r['type']+(' NOT NULL' if r['notnull'] else '') for r in info)
    require(not conn.execute('SELECT 1 FROM sqlite_master WHERE name=?', (STAGING,)).fetchone(),
            'lifetime_migration_staging_exists')
    source = [tuple(r) for r in conn.execute('SELECT '+names+' FROM '+authority.AUTHORITIES+' ORDER BY authority_id')]
    objects = conn.execute("SELECT type,name,tbl_name,sql FROM sqlite_master WHERE sql IS NOT NULL").fetchall()
    known = {**authority.definitions(), **attempts.definitions()}
    dependent = []
    for row in objects:
        if row['type'] in ('trigger', 'index') and (row['tbl_name'] == authority.AUTHORITIES
                                                   or authority.AUTHORITIES in row['sql']):
            require(row['name'] in known and ' '.join(row['sql'].split()) == ' '.join(known[row['name']].split()),
                    'lifetime_migration_unknown_dependent')
            dependent.append(row)
    conn.execute('PRAGMA defer_foreign_keys=ON')
    conn.execute('CREATE TABLE main.'+STAGING+' ('+columns+')')
    conn.execute('INSERT INTO main.'+STAGING+' ('+names+') SELECT '+names+' FROM '+authority.AUTHORITIES)
    require([tuple(r) for r in conn.execute('SELECT '+names+' FROM main.'+STAGING+' ORDER BY authority_id')] == source,
            'lifetime_migration_staging_mismatch')
    for row in dependent:
        conn.execute('DROP '+row['type'].upper()+' '+_quote(row['name']))
    conn.execute('DROP TABLE '+authority.AUTHORITIES)
    successor = lineage.successor_definitions()
    conn.execute(successor[authority.AUTHORITIES])
    conn.execute('INSERT INTO '+authority.AUTHORITIES+' ('+names+') SELECT '+names+' FROM main.'+STAGING)
    for row in dependent:
        conn.execute(successor.get(row['name'], row['sql']))
    require([tuple(r) for r in conn.execute('SELECT '+names+' FROM '+authority.AUTHORITIES+' ORDER BY authority_id')] == source,
            'lifetime_migration_copy_mismatch')
    conn.execute('DROP TABLE main.'+STAGING)
    require(not conn.execute('PRAGMA foreign_key_check').fetchone(), 'lifetime_migration_foreign_key_mismatch')


def migrate(config, *, expected_generation, operator, reason):
    """Explicit trusted-local migration; target query-only through control commit.

    Lost commit/cleanup acknowledgement requires durable inspection. Never retry,
    repair or adopt automatically. No key-content access or generation advance.
    """
    from . import runtime_challenges as challenges, runtime_validation as runtime, local_readiness
    require(type(config) is admin.LocalAdministration, 'local_administration_required')
    config.paths(); operation._positive(expected_generation)
    runtime.enrollment._text(operator, 200); authority._reason(reason)
    with admin.connect(config.control, write=True) as control:
        control.execute('BEGIN IMMEDIATE')
        base.check_control(control)
        require(authority._present(control), 'lifetime_migration_prerequisites')
        binding = challenges._deployment_binding(control)
        require(binding['generation'] == expected_generation, 'lifetime_migration_generation_conflict')
        require(asdict(admin.target_identity(control)) == binding['control_identity'], 'control_identity_mismatch')
        require(binding['production_state'] == 'NOT_ACTIVATED'
                and local_readiness._state(control, binding)['state'] == 'NOT_ACTIVATED',
                'lifetime_migration_requires_not_activated')
        if binding['runtime_profile_sha256'] is not None:
            runtime._history(control)
        with admin.connect(config.target, write=True) as target:
            target.execute('BEGIN IMMEDIATE'); target.execute('PRAGMA query_only=ON')
            admin._verify(config, control, target, binding)
            for path in (config.control, config.target):
                with admin.connect(path) as preflight:
                    require([r[0] for r in preflight.execute('PRAGMA integrity_check')] == ['ok']
                            and not preflight.execute('PRAGMA foreign_key_check').fetchone(),
                            'lifetime_migration_integrity')
            if lineage.present(control):
                lineage.verify(control)
                control.rollback()
                return dict(migration_id=MIGRATION, installed=False, generation=expected_generation)
            require(all(load(r[0])['lifetime_policy'] == authority.LIFETIME for r in control.execute(
                'SELECT body_json FROM '+authority.AUTHORITIES)), 'lifetime_migration_requires_v1')
            previous = claims.manifest(control)
            before = _snapshot(control)
            now = runtime._utc_now(); head = admin._audit_head(control)
            require(head is None or authority._time(now) >= authority._time(load(head['body_json'])['at_utc']),
                    'administrative_clock_rollback')
            target_changes = target.total_changes
            control.execute('SAVEPOINT upgrade_authority_lifetime_policy')
            try:
                _rebuild(control)
                require(_snapshot(control) == before, 'lifetime_migration_rows_changed')
                admin._audit(control, ACTION, operator, now, dict(migration_id=MIGRATION,
                    previous_schema_sha256=previous, installed_schema_sha256=claims.manifest(control),
                    installation_id=binding['installation_id'], generation=expected_generation, reason=reason))
                base.check_control(control)
                after = _snapshot(control)
                audit_table = 'recognition_admin_audit'
                require(set(before) == set(after)
                        and all(after[n] == rows for n, rows in before.items() if n != audit_table)
                        and after[audit_table][:-1] == before[audit_table]
                        and len(after[audit_table]) == len(before[audit_table])+1,
                        'lifetime_migration_protected_rows_changed')
                require(challenges._deployment_binding(control) == binding
                        and asdict(admin.target_identity(control)) == binding['control_identity'],
                        'lifetime_migration_scope_changed')
                admin._verify(config, control, target, binding)
                require(target.total_changes == target_changes and target.execute('PRAGMA query_only').fetchone()[0] == 1,
                        'lifetime_migration_target_changed')
                require(authority._time(runtime._utc_now()) >= authority._time(now), 'administrative_clock_rollback')
                control.execute('RELEASE upgrade_authority_lifetime_policy')
                control.commit()
                require(not control.in_transaction and target.in_transaction, 'lifetime_migration_commit_unconfirmed')
                with admin.connect(config.control) as verification:
                    verification.execute('BEGIN')
                    base.check_control(verification)
                    require([r[0] for r in verification.execute('PRAGMA integrity_check')] == ['ok']
                            and not verification.execute('PRAGMA foreign_key_check').fetchone(),
                            'lifetime_migration_integrity')
            except BaseException:
                if control.in_transaction:
                    control.rollback()
                raise
    return dict(migration_id=MIGRATION, installed=True, generation=expected_generation)

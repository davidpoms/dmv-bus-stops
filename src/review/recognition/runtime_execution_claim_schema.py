"""Explicit control storage only. No execution-claim issuer or writer authority."""

from . import runtime_profile_schema as p
from .rules import canonical, digest
from .trust import fields, identity, load, require, utc


MIGRATION = 'recognition-runtime-execution-claims-v1'
CLAIMS = 'recognition_runtime_execution_claims'
HISTORY = 'recognition_runtime_execution_claim_history'
FORMAT = 'recognition-runtime-execution-claim-v1'
EVENT_FORMAT = 'recognition-runtime-execution-claim-event-v1'
ACTION = 'runtime_execution_claim_schema_installed'


def definitions():
    c = p.column
    sha_fields = ('operation_sha256','proposal_sha256','acknowledgement_sha256','approval_sha256',
                  'approval_history_sha256','dependency_snapshot_sha256','target_snapshot_sha256',
                  'admission_sha256','emergency_stop_snapshot_sha256')
    body_checks = ' AND '.join(p.sha(f"json_extract(body_json,'$.{key}')") for key in sha_fields)
    body_checks += ' AND '+p.uuid("json_extract(body_json,'$.approval_id')")
    tables = {
        CLAIMS: [c('claim_id', 'TEXT', p.uuid('claim_id')),
            c('operation_id', 'TEXT', p.uuid('operation_id')),
            c('body_json', 'TEXT', "typeof(body_json)='text' AND instr(body_json,char(0))=0 AND json_valid(body_json) AND json_type(body_json)='object'"),
            c('body_sha256', 'TEXT', p.sha('body_sha256')),
            c('generation', 'INTEGER', p.integer('generation', 1, 2**63-1)),
            c('profile_sha256', 'TEXT', p.sha('profile_sha256')),
            c('issued_at', 'INTEGER', p.integer('issued_at', 0, p.MAX_TIME-300)),
            c('expires_at', 'INTEGER', p.integer('expires_at')),
            c('audit_sequence', 'INTEGER', p.integer('audit_sequence', 1, 2**63-1)),
            'PRIMARY KEY(claim_id)', 'UNIQUE(operation_id)', 'UNIQUE(body_sha256)', 'UNIQUE(audit_sequence)',
            'CHECK(expires_at=issued_at+300 AND expires_at>issued_at)',
            f'CHECK({body_checks})',
            'FOREIGN KEY(generation) REFERENCES recognition_admin_bindings(generation)',
            f'FOREIGN KEY(profile_sha256) REFERENCES {p.PROFILES}(profile_sha256)',
            'FOREIGN KEY(audit_sequence) REFERENCES recognition_admin_audit(sequence) DEFERRABLE INITIALLY DEFERRED'],
        HISTORY: [c('claim_id', 'TEXT', p.uuid('claim_id')),
            c('sequence', 'INTEGER', p.integer('sequence', 1, 2**63-1)),
            c('state', 'TEXT', "state IN ('ISSUED','CONSUMED','EXPIRED','REVOKED','RECOVERY_REQUIRED')"),
            c('at', 'INTEGER', p.integer('at')),
            c('body_json', 'TEXT', "typeof(body_json)='text' AND instr(body_json,char(0))=0 AND json_valid(body_json) AND json_type(body_json)='object'"),
            c('body_sha256', 'TEXT', p.sha('body_sha256')),
            c('audit_sequence', 'INTEGER', p.integer('audit_sequence', 1, 2**63-1)),
            'PRIMARY KEY(claim_id,sequence)', 'UNIQUE(body_sha256)', 'UNIQUE(audit_sequence)',
            f'FOREIGN KEY(claim_id) REFERENCES {CLAIMS}(claim_id)',
            'FOREIGN KEY(audit_sequence) REFERENCES recognition_admin_audit(sequence) DEFERRABLE INITIALLY DEFERRED']}
    result = {name: f"CREATE TABLE {name} ({', '.join(columns)})" for name, columns in tables.items()}
    keys = {CLAIMS: [('claim_id',), ('operation_id',), ('body_sha256',), ('audit_sequence',)],
            HISTORY: [('claim_id','sequence'), ('body_sha256',), ('audit_sequence',)]}
    for table in tables:
        for verb in ('UPDATE','DELETE'):
            name = table+'_immutable_'+verb.lower()
            result[name] = f"CREATE TRIGGER {name} BEFORE {verb} ON {table} BEGIN SELECT RAISE(ABORT,'immutable_runtime_execution_claim'); END"
        name = table+'_immutable_replace'
        collision = ' OR '.join('('+' AND '.join(f'{key}=NEW.{key}' for key in group)+')' for group in keys[table])
        result[name] = f"CREATE TRIGGER {name} BEFORE INSERT ON {table} WHEN EXISTS(SELECT 1 FROM {table} WHERE {collision}) BEGIN SELECT RAISE(ABORT,'immutable_runtime_execution_claim'); END"
    name = CLAIMS+'_scope_idx'
    result[name] = f'CREATE INDEX {name} ON {CLAIMS}(generation,profile_sha256)'
    def guard(name, table, condition):
        result[name] = (f'CREATE TRIGGER {name} BEFORE INSERT ON {table} WHEN NOT COALESCE(({condition}),0) '
                        "BEGIN SELECT RAISE(ABORT,'runtime_execution_claim_scope_mismatch'); END")
    j = lambda path: f"json_extract(NEW.body_json,'$.{path}')"
    typed = ' AND '.join(f"json_type(NEW.body_json,'$.{key}')='integer'" for key in
        ('runtime_scope.generation','runtime_scope.owner_id','runtime_scope.auth_epoch','runtime_scope.mfa_epoch',
         'authentication.actor_id','proposal_reference.acknowledgement_sequence'))
    physical = []
    for prefix,path in (('target','target_snapshot.target.observation'),('control','target_snapshot.control_identity')):
        physical.extend((f"r.hostname={j(path+'.hostname')}",f"r.{prefix}_path={j(path+'.database')}"))
        for key in ('device','inode'):
            physical.append(f"json_type(NEW.body_json,'$.{path}.{key}')='integer'")
            physical.append(f"r.{prefix}_{key}=(NEW.body_json -> '$.{path}.{key}')")
    guard(CLAIMS+'_scope_guard', CLAIMS,
        f"{typed} AND {j('format')}='{FORMAT}' AND {j('state')}='ISSUED' AND {j('claim_id')}=NEW.claim_id "
        f"AND {j('runtime_scope.format')}='recognition-runtime-operation-target-v1' "
        f"AND {j('proposal_reference.format')}='recognition-runtime-proposal-reference-v1' "
        f"AND {j('proposal_reference.operation_id')}=NEW.operation_id "
        f"AND {j('proposal_reference.operation_sha256')}={j('operation_sha256')} AND {j('proposal_sha256')}={j('operation_sha256')} "
        f"AND {j('proposal_reference.acknowledgement_sha256')}={j('acknowledgement_sha256')} "
        f"AND {j('proposal_reference.acknowledgement_sequence')}>0 "
        f"AND {j('operation_id')}=NEW.operation_id AND {j('runtime_scope.generation')}=NEW.generation "
        f"AND {j('runtime_scope.runtime_profile_sha256')}=NEW.profile_sha256 "
        f"AND {j('issued_at_utc')}=strftime('%Y-%m-%dT%H:%M:%SZ',NEW.issued_at,'unixepoch') "
        f"AND {j('expires_at_utc')}=strftime('%Y-%m-%dT%H:%M:%SZ',NEW.expires_at,'unixepoch') "
        'AND NOT EXISTS(SELECT 1 FROM recognition_admin_audit WHERE sequence=NEW.audit_sequence) '
        f'AND EXISTS(SELECT 1 FROM recognition_admin_bindings b JOIN {p.PROFILES} r ON r.generation=b.generation '
        f"WHERE b.generation=NEW.generation AND r.profile_sha256=NEW.profile_sha256 "
        'AND b.generation=(SELECT MAX(generation) FROM recognition_admin_bindings) '
        f"AND b.body_sha256={j('runtime_scope.binding_sha256')} "
        "AND json_extract(b.body_json,'$.production_state')='NOT_ACTIVATED' "
        "AND json_extract(b.body_json,'$.runtime_profile_sha256')=r.profile_sha256 "
        f"AND r.installation_id={j('runtime_scope.installation_id')} AND r.target_id={j('runtime_scope.target_id')} "
        f"AND r.target_schema_sha256={j('target_snapshot.target.schema_sha256')} AND {' AND '.join(physical)} "
        f"AND r.owner_id={j('runtime_scope.owner_id')} AND EXISTS(SELECT 1 FROM recognition_admin_primary x "
        f'JOIN recognition_admin_sessions s ON s.primary_hash=x.token_hash JOIN {p.AUTH} xp '
        f"ON xp.token_kind='primary' AND xp.token_hash=x.token_hash JOIN {p.AUTH} sp "
        "ON sp.token_kind='session' AND sp.token_hash=s.token_hash JOIN recognition_admin_mfa m ON m.actor=s.actor "
        f"WHERE x.token_hash={j('authentication.primary_sha256')} AND s.token_hash={j('authentication.session_sha256')} "
        f"AND {j('authentication.actor_id')}=r.owner_id AND x.actor=r.owner_id AND s.actor=r.owner_id "
        'AND x.generation=r.generation AND s.generation=r.generation AND x.revoked=0 AND s.revoked=0 '
        'AND xp.profile_sha256=r.profile_sha256 AND sp.profile_sha256=r.profile_sha256 '
        f"AND x.auth_epoch={j('runtime_scope.auth_epoch')} AND s.auth_epoch=x.auth_epoch "
        f"AND s.mfa_epoch={j('runtime_scope.mfa_epoch')} AND m.epoch=s.mfa_epoch AND m.state='ENROLLED' "
        'AND x.created<=NEW.issued_at AND s.created<=NEW.issued_at AND x.expires>=NEW.expires_at AND s.expires>=NEW.expires_at))')
    guard(HISTORY+'_transition', HISTORY,
        f"{j('format')}='{EVENT_FORMAT}' AND {j('claim_id')}=NEW.claim_id AND {j('sequence')}=NEW.sequence "
        f"AND json_type(NEW.body_json,'$.sequence')='integer' AND {p.text(j('reason'),2000)} "
        f"AND {j('state')}=NEW.state AND {j('at_utc')}=strftime('%Y-%m-%dT%H:%M:%SZ',NEW.at,'unixepoch') "
        'AND NOT EXISTS(SELECT 1 FROM recognition_admin_audit WHERE sequence=NEW.audit_sequence) '
        f'AND NEW.sequence=COALESCE((SELECT MAX(sequence) FROM {HISTORY} WHERE claim_id=NEW.claim_id),0)+1 '
        f'AND EXISTS(SELECT 1 FROM {CLAIMS} c WHERE c.claim_id=NEW.claim_id '
        f"AND c.body_sha256={j('claim_sha256')} AND NEW.at>=c.issued_at AND "
        f"((NEW.sequence=1 AND NEW.state='ISSUED' AND NEW.at=c.issued_at AND NEW.audit_sequence=c.audit_sequence "
        "AND json_type(NEW.body_json,'$.previous_sha256')='null') OR "
        f'(NEW.sequence>1 AND EXISTS(SELECT 1 FROM {HISTORY} h WHERE h.claim_id=NEW.claim_id '
        f"AND h.sequence=NEW.sequence-1 AND h.body_sha256={j('previous_sha256')} AND NEW.at>=h.at "
        "AND ((h.state='ISSUED' AND NEW.state IN ('CONSUMED','EXPIRED','REVOKED','RECOVERY_REQUIRED')) "
        "OR (h.state='CONSUMED' AND NEW.state='RECOVERY_REQUIRED'))))) "
        "AND (NEW.state!='CONSUMED' OR NEW.at<c.expires_at) AND (NEW.state!='EXPIRED' OR NEW.at>=c.expires_at))")
    # The deferred FK forces this audit to exist; the audit must be inserted last.
    name = CLAIMS+'_audit_guard'
    result[name] = f"""CREATE TRIGGER {name} BEFORE INSERT ON recognition_admin_audit
        WHEN EXISTS(SELECT 1 FROM {CLAIMS} WHERE audit_sequence=NEW.sequence)
          OR EXISTS(SELECT 1 FROM {HISTORY} WHERE audit_sequence=NEW.sequence)
        BEGIN SELECT CASE WHEN NOT EXISTS(SELECT 1 FROM {HISTORY} h JOIN {CLAIMS} c ON c.claim_id=h.claim_id
          WHERE h.audit_sequence=NEW.sequence
          AND json_type(NEW.body_json,'$.actor')='integer'
          AND json_type(NEW.body_json,'$.subject.event_sequence')='integer'
          AND json_extract(NEW.body_json,'$.actor')=json_extract(c.body_json,'$.runtime_scope.owner_id')
          AND json_extract(NEW.body_json,'$.at_utc')=json_extract(h.body_json,'$.at_utc')
          AND json_extract(NEW.body_json,'$.subject.claim_id')=c.claim_id
          AND json_extract(NEW.body_json,'$.subject.claim_sha256')=c.body_sha256
          AND json_extract(NEW.body_json,'$.subject.event_sequence')=h.sequence
          AND json_extract(NEW.body_json,'$.subject.event_sha256')=h.body_sha256
          AND json_extract(NEW.body_json,'$.action')=CASE WHEN h.sequence=1 THEN
            'runtime_execution_claim_issued' ELSE 'runtime_execution_claim_state_changed' END)
        THEN RAISE(ABORT,'runtime_execution_claim_audit_mismatch') END; END"""
    return result


def _body(encoded, hashed):
    body = load(encoded)
    from .runtime_operation_contract import _json
    _json(body)
    require(canonical(body) == encoded and digest(body) == hashed, 'runtime_execution_claim_digest_mismatch')
    return body


def check_rows(conn):
    """Historical storage validation only; never current execution admission."""
    from . import administration as a, runtime_operation_contract as operation
    from . import runtime_validation as runtime, runtime_approval_ceremony as ceremony
    from .runtime_activation_authority_schema import historical_claim_manifest
    installs = [row for row in conn.execute('SELECT body_json,body_sha256 FROM recognition_admin_audit')
                if load(row['body_json']).get('action') == ACTION]
    require(len(installs) == 1, 'runtime_claim_migration_audit_mismatch')
    installed = _body(installs[0]['body_json'],installs[0]['body_sha256'])
    subject = installed['subject']
    fields(subject,('migration_id','previous_schema_sha256','installed_schema_sha256','installation_id','generation','reason'))
    require(subject['migration_id'] == MIGRATION and subject['installed_schema_sha256'] == historical_claim_manifest(conn),
            'runtime_claim_migration_audit_mismatch')
    for key in ('previous_schema_sha256','installed_schema_sha256'):
        p._check_sha(subject[key])
    require(subject['previous_schema_sha256'] == historical_claim_manifest(conn,exclude=definitions()),'runtime_claim_migration_audit_mismatch')
    identity(subject['installation_id'])
    runtime.enrollment._integer(subject['generation'],1,2**63-1)
    source = conn.execute('SELECT body_json FROM recognition_admin_bindings WHERE generation=?',(subject['generation'],)).fetchone()
    require(source is not None and load(source[0])['installation_id'] == subject['installation_id'],
            'runtime_claim_migration_audit_mismatch')
    runtime.enrollment._text(installed['actor'],200)
    runtime.enrollment._text(subject['reason'],2000)
    utc(installed['at_utc'])
    names = ('format claim_id operation_id operation_sha256 proposal_sha256 proposal_reference '
             'acknowledgement_sha256 approval_id approval_sha256 approval_history_sha256 runtime_scope '
             'authentication dependency_snapshot_sha256 target_snapshot target_snapshot_sha256 '
             'admission_sha256 emergency_stop_snapshot_sha256 issued_at_utc expires_at_utc state').split()
    for row in conn.execute(f'SELECT * FROM {CLAIMS}'):
        value = _body(row['body_json'], row['body_sha256'])
        fields(value, names)
        require(value['format'] == FORMAT and value['state'] == 'ISSUED', 'runtime_execution_claim_format')
        for key in ('claim_id','operation_id','approval_id'):
            identity(value[key])
        for key in names:
            if key.endswith('_sha256'):
                p._check_sha(value[key])
        scope = value['runtime_scope']
        operation._shape(scope)
        ceremony._reference(value['proposal_reference'])
        reference = value['proposal_reference']
        require(reference['operation_id'] == value['operation_id']
                and reference['operation_sha256'] == value['operation_sha256'] == value['proposal_sha256']
                and reference['acknowledgement_sha256'] == value['acknowledgement_sha256'], 'runtime_execution_claim_proposal')
        issued, expires = a.timestamp(value['issued_at_utc']), a.timestamp(value['expires_at_utc'])
        require(expires == issued+300 and (row['claim_id'],row['operation_id'],row['generation'],row['profile_sha256'],
                row['issued_at'],row['expires_at']) == (value['claim_id'],value['operation_id'],scope['generation'],
                scope['runtime_profile_sha256'],issued,expires), 'runtime_execution_claim_columns')
        binding = conn.execute('SELECT body_json,body_sha256 FROM recognition_admin_bindings WHERE generation=?',
                               (scope['generation'],)).fetchone()
        profile = conn.execute(f'SELECT * FROM {p.PROFILES} WHERE profile_sha256=?', (row['profile_sha256'],)).fetchone()
        require(binding is not None and profile is not None and binding['body_sha256'] == scope['binding_sha256'],
                'runtime_execution_claim_binding')
        bound = load(binding['body_json'])
        require(all(scope[k] == bound[k] == profile[k] for k in ('generation','installation_id','target_id','owner_id'))
                and bound['runtime_profile_sha256'] == row['profile_sha256'], 'runtime_execution_claim_binding')
        proof = value['authentication']
        fields(proof, ('actor_id','primary_sha256','session_sha256'))
        require(type(proof['actor_id']) is int and proof['actor_id'] == scope['owner_id'], 'runtime_execution_claim_actor')
        for kind, table in (('primary','recognition_admin_primary'),('session','recognition_admin_sessions')):
            hashed = proof[kind+'_sha256']
            p._check_sha(hashed)
            record = conn.execute(f'SELECT * FROM {table} WHERE token_hash=?', (hashed,)).fetchone()
            link = conn.execute(f'SELECT profile_sha256 FROM {p.AUTH} WHERE token_kind=? AND token_hash=?',
                                (kind,hashed)).fetchone()
            require(record is not None and link is not None and link[0] == row['profile_sha256']
                    and record['actor'] == scope['owner_id'] and record['generation'] == scope['generation']
                    and record['auth_epoch'] == scope['auth_epoch'] and record['created'] <= issued
                    and record['expires'] >= expires, 'runtime_execution_claim_authentication')
            if kind == 'session':
                require(record['primary_hash'] == proof['primary_sha256'] and record['mfa_epoch'] == scope['mfa_epoch'],
                        'runtime_execution_claim_authentication')
        snapshot = value['target_snapshot']
        fields(snapshot, ('target','control_identity'))
        fields(snapshot['target'], ('observation','schema_sha256'))
        require(digest(snapshot) == value['target_snapshot_sha256']
                and snapshot['target']['schema_sha256'] == profile['target_schema_sha256']
                == bound['target']['schema_sha256'], 'runtime_execution_claim_target_snapshot')
        for prefix, physical in (('target',snapshot['target']['observation']),('control',snapshot['control_identity'])):
            runtime._physical(physical)
            require(physical['hostname'] == profile['hostname'] and physical['database'] == profile[prefix+'_path']
                    and str(physical['device']) == profile[prefix+'_device']
                    and str(physical['inode']) == profile[prefix+'_inode'], 'runtime_execution_claim_physical_identity')
        previous, last_time, last_state = None, issued, None
        history = conn.execute(f'SELECT * FROM {HISTORY} WHERE claim_id=? ORDER BY sequence', (row['claim_id'],)).fetchall()
        require(bool(history), 'runtime_execution_claim_genesis_missing')
        for sequence, event in enumerate(history,1):
            body = _body(event['body_json'],event['body_sha256'])
            fields(body, ('format','claim_id','claim_sha256','sequence','previous_sha256','state','reason','at_utc'))
            moment = a.timestamp(body['at_utc'])
            require(body['format'] == EVENT_FORMAT and body['claim_id'] == row['claim_id']
                    and body['claim_sha256'] == row['body_sha256'] and type(body['sequence']) is int
                    and body['sequence'] == event['sequence'] == sequence and body['previous_sha256'] == previous
                    and body['state'] == event['state'] and moment == event['at'] and moment >= last_time,
                    'runtime_execution_claim_history')
            runtime.enrollment._text(body['reason'],2000)
            allowed = {'ISSUED': {'CONSUMED','EXPIRED','REVOKED','RECOVERY_REQUIRED'}, 'CONSUMED': {'RECOVERY_REQUIRED'}}
            require((sequence == 1 and body['state'] == 'ISSUED' and moment == issued
                     and event['audit_sequence'] == row['audit_sequence'])
                    or (sequence > 1 and body['state'] in allowed.get(last_state,set())), 'runtime_execution_claim_transition')
            require((body['state'] != 'CONSUMED' or moment < expires)
                    and (body['state'] != 'EXPIRED' or moment >= expires), 'runtime_execution_claim_expiry')
            audit = conn.execute('SELECT body_json,body_sha256 FROM recognition_admin_audit WHERE sequence=?',
                                 (event['audit_sequence'],)).fetchone()
            require(audit is not None, 'runtime_execution_claim_audit_missing')
            audit_body = _body(audit['body_json'],audit['body_sha256'])
            require(type(audit_body['actor']) is int and audit_body['actor'] == scope['owner_id']
                    and type(audit_body['subject'].get('event_sequence')) is int and audit_body['at_utc'] == body['at_utc']
                    and audit_body['action'] == ('runtime_execution_claim_issued' if sequence == 1 else 'runtime_execution_claim_state_changed')
                    and audit_body['subject'] == dict(claim_id=row['claim_id'],claim_sha256=row['body_sha256'],
                        event_sequence=sequence,event_sha256=event['body_sha256']), 'runtime_execution_claim_audit_mismatch')
            previous,last_time,last_state = event['body_sha256'],moment,body['state']
    require(not conn.execute('PRAGMA foreign_key_check').fetchone(), 'runtime_execution_claim_foreign_key_mismatch')


def manifest(conn, *, exclude=()):
    """Same whitespace-normalized exact definitions used by check_control."""
    from .administration_schema import _control_objects
    return digest({name:' '.join(sql.split()) for name,sql in _control_objects(conn) if name not in exclude})


def migrate(config, *, expected_generation, operator, reason):
    """Explicit trusted deployment migration; storage only, target query-only.

    Lost commit acknowledgement requires durable inspection, never blind retry.
    No CLI/web route, key-content read, profile transition or claim creation.
    """
    from dataclasses import asdict
    from . import administration as a, administration_schema as schema
    from . import runtime_challenges as challenges, runtime_validation as runtime
    require(type(config) is a.LocalAdministration, 'local_administration_required')
    config.paths()
    runtime.enrollment._integer(expected_generation,1,2**63-1)
    runtime.enrollment._text(operator,200)
    runtime.enrollment._text(reason,2000)
    with a.connect(config.control,write=True) as control:
        control.execute('BEGIN IMMEDIATE')
        schema.check_control(control)
        binding = challenges._deployment_binding(control)
        require(binding['generation'] == expected_generation, 'runtime_claim_migration_generation_conflict')
        require(binding['production_state'] == 'NOT_ACTIVATED', 'runtime_claim_migration_requires_not_activated')
        require(asdict(a.target_identity(control)) == binding['control_identity'], 'control_identity_mismatch')
        if binding['runtime_profile_sha256'] is not None:
            runtime._history(control)  # Durable enrollment only; console is not runtime.
        with a.connect(config.target,write=True) as target:
            target.execute('BEGIN IMMEDIATE')
            target.execute('PRAGMA query_only=ON')
            a._verify(config,control,target,binding)
            if control.execute("SELECT 1 FROM sqlite_master WHERE name='recognition_local_activation'").fetchone():
                from .local_readiness import _state
                require(_state(control,binding)['state'] == 'NOT_ACTIVATED','runtime_claim_migration_requires_not_activated')
            # integrity_check can initialize temp on its connection. Keep the
            # existing single-database control-connection invariant unchanged.
            # Both writer reservations stay held; these readers see the same
            # committed, unmodified stores and cannot perform recovery writes.
            for path in (config.control,config.target):
                with a.connect(path) as preflight:
                    require([r[0] for r in preflight.execute('PRAGMA integrity_check')] == ['ok'],
                            'runtime_claim_migration_integrity_failure')
                    require(not preflight.execute('PRAGMA foreign_key_check').fetchone(),'runtime_claim_migration_foreign_key_failure')
            head = a._audit_head(control)
            audits = [load(row[0]) for row in control.execute('SELECT body_json FROM recognition_admin_audit')
                      if load(row[0]).get('action') == ACTION]
            installed = bool(control.execute("SELECT 1 FROM sqlite_master WHERE name=?",(CLAIMS,)).fetchone())
            if installed:
                from .runtime_activation_authority_schema import historical_claim_manifest
                require(len(audits) == 1 and audits[0]['subject']['migration_id'] == MIGRATION
                        and audits[0]['subject']['installed_schema_sha256'] == historical_claim_manifest(control),
                        'runtime_claim_migration_audit_mismatch')
                control.rollback()  # Resolve control before releasing target, also on no-op.
                return dict(migration_id=MIGRATION,installed=False,generation=expected_generation)
            require(not audits,'runtime_claim_migration_audit_mismatch')
            old_manifest = manifest(control)
            now = runtime._utc_now()
            require(head is None or a.timestamp(now) >= a.timestamp(load(head['body_json'])['at_utc']),
                    'administrative_clock_rollback')
            target_changes = target.total_changes
            control.execute('SAVEPOINT install_runtime_execution_claims')
            try:
                for sql in definitions().values():
                    control.execute(sql)
                a._audit(control,ACTION,operator,now,dict(migration_id=MIGRATION,
                    previous_schema_sha256=old_manifest,installed_schema_sha256=manifest(control),
                    installation_id=binding['installation_id'],generation=expected_generation,reason=reason))
                schema.check_control(control)
                a._audit_head(control)
                require(challenges._deployment_binding(control) == binding,'runtime_claim_migration_binding_changed')
                require(asdict(a.target_identity(control)) == binding['control_identity'],'control_identity_mismatch')
                a._verify(config,control,target,binding)
                require(target.total_changes == target_changes and target.execute('PRAGMA query_only').fetchone()[0] == 1,
                        'runtime_claim_migration_target_changed')
                require(a.timestamp(runtime._utc_now()) >= a.timestamp(now),'administrative_clock_rollback')
                control.execute('RELEASE install_runtime_execution_claims')
                control.commit()  # Target reservation remains held through COMMIT.
            except BaseException:
                if control.in_transaction:
                    control.rollback()
                raise
    return dict(migration_id=MIGRATION,installed=True,generation=expected_generation)

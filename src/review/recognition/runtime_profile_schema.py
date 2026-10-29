"""Slice 1 control-store definitions only; no runtime enrollment or authority."""

from pathlib import Path
import re
from uuid import UUID

from .rules import digest
from .trust import require, load, utc


CHALLENGES = "recognition_runtime_enrollment_challenges"
PROFILES = "recognition_runtime_profiles"
AUTH = "recognition_runtime_auth_bindings"
V3 = "recognition-local-control-v3"
MAX_TIME = 253402300799  # Last whole UTC second representable by datetime.


def sha(name):
    return f"typeof({name})='text' AND instr({name},char(0))=0 AND length({name})=64 AND {name} NOT GLOB '*[^0-9a-f]*'"


def uuid(name):
    return (f"typeof({name})='text' AND instr({name},char(0))=0 AND length({name})=36 AND substr({name},9,1)='-' "
            f"AND substr({name},14,1)='-' AND substr({name},19,1)='-' AND substr({name},24,1)='-' "
            f"AND length(replace({name},'-',''))=32 AND replace({name},'-','') NOT GLOB '*[^0-9a-f]*'")


def integer(name, low=0, high=MAX_TIME):
    return f"typeof({name})='integer' AND {name} BETWEEN {low} AND {high}"


def text(name, maximum=None):
    limit = f" AND length({name})<={maximum}" if maximum else ""
    return f"typeof({name})='text' AND length(trim({name}))>0 AND instr({name},char(0))=0{limit}"


def decimal(name, inode=False):
    return (f"typeof({name})='text' AND instr({name},char(0))=0 AND length({name})>=1 AND {name} NOT GLOB '*[^0-9]*' "
            f"AND ({name}='0' OR substr({name},1,1) BETWEEN '1' AND '9')" +
            (f" AND {name}<>'0'" if inode else ""))


def path(name):
    # Lexical checks are portable. Full canonical-path validation also runs in check_rows.
    p = f"replace({name},char(92),'/')"
    return (f"{text(name)} AND (substr({name},1,1)='/' OR "
            f"(substr({name},1,1) GLOB '[A-Za-z]' AND substr({name},2,1)=':' "
            f"AND substr({name},3,1)=char(92))) AND {p} NOT LIKE '%//%' "
            f"AND {p} NOT LIKE '%/./%' AND {p} NOT LIKE '%/../%' "
            f"AND {p} NOT LIKE '%/.' AND {p} NOT LIKE '%/..' AND substr({p},-1)<>'/'")


def column(name, kind, check):
    return f"{name} {kind} NOT NULL CHECK({check})"


def definitions():
    c = column
    challenges = [
        c('challenge_id', 'TEXT', uuid('challenge_id')),
        c('format', 'TEXT', "format='recognition-runtime-enrollment-challenge-v1'"),
        c('installation_id', 'TEXT', uuid('installation_id')),
        c('source_generation', 'INTEGER', integer('source_generation', 1, 9223372036854775807)),
        c('source_binding_sha256', 'TEXT', sha('source_binding_sha256')),
        c('target_id', 'TEXT', uuid('target_id')), c('owner_id', 'INTEGER', integer('owner_id', 1, 9223372036854775807)),
        c('role', 'TEXT', "role='runtime'"), c('nonce_sha256', 'TEXT', sha('nonce_sha256')),
        c('issued_at', 'INTEGER', integer('issued_at')), c('expires_at', 'INTEGER', integer('expires_at')),
        c('operator', 'TEXT', text('operator', 200)), c('reason', 'TEXT', text('reason', 2000)),
        c('audit_sequence', 'INTEGER', integer('audit_sequence', 1, 9223372036854775807)),
        c('challenge_sha256', 'TEXT', sha('challenge_sha256')),
        'PRIMARY KEY(challenge_id)', 'UNIQUE(nonce_sha256)', 'UNIQUE(audit_sequence)', 'UNIQUE(challenge_sha256)',
        'CHECK(expires_at=issued_at+600)',
        'FOREIGN KEY(source_generation) REFERENCES recognition_admin_bindings(generation)',
        'FOREIGN KEY(audit_sequence) REFERENCES recognition_admin_audit(sequence) DEFERRABLE INITIALLY DEFERRED',
    ]
    profiles = [c('profile_sha256', 'TEXT', sha('profile_sha256')),
        c('format', 'TEXT', "format='recognition-runtime-profile-v1'"),
        c('installation_id', 'TEXT', uuid('installation_id')),
        c('generation', 'INTEGER', integer('generation', 1, 9223372036854775807)),
        c('role', 'TEXT', "role='runtime'"), c('hostname', 'TEXT', text('hostname'))]
    for prefix in ('target', 'control'):
        profiles.extend((c(prefix+'_path', 'TEXT', path(prefix+'_path')),
                         c(prefix+'_device', 'TEXT', decimal(prefix+'_device')),
                         c(prefix+'_inode', 'TEXT', decimal(prefix+'_inode', True))))
    profiles.extend((c('target_schema_sha256', 'TEXT', sha('target_schema_sha256')),
        c('target_id', 'TEXT', uuid('target_id')), c('owner_id', 'INTEGER', integer('owner_id', 1, 9223372036854775807)),
        c('challenge_id', 'TEXT', uuid('challenge_id')), c('observation_sha256', 'TEXT', sha('observation_sha256')),
        c('evidence_channel', 'TEXT', "evidence_channel='operator-reviewed-private-wsgi-log-v1'"),
        c('observed_at', 'INTEGER', integer('observed_at')), c('created_at', 'INTEGER', integer('created_at')),
        c('operator', 'TEXT', text('operator', 200)), c('reason', 'TEXT', text('reason', 2000)),
        c('audit_sequence', 'INTEGER', integer('audit_sequence', 1, 9223372036854775807)),
        'PRIMARY KEY(profile_sha256)', 'UNIQUE(installation_id,generation,role)', 'UNIQUE(generation,role)',
        'UNIQUE(challenge_id)', 'UNIQUE(audit_sequence)', 'CHECK(created_at>=observed_at)',
        'FOREIGN KEY(generation) REFERENCES recognition_admin_bindings(generation) DEFERRABLE INITIALLY DEFERRED',
        f'FOREIGN KEY(challenge_id) REFERENCES {CHALLENGES}(challenge_id)',
        'FOREIGN KEY(audit_sequence) REFERENCES recognition_admin_audit(sequence) DEFERRABLE INITIALLY DEFERRED'))
    auth = [c('token_kind', 'TEXT', "token_kind IN ('primary','session')"), c('token_hash', 'TEXT', sha('token_hash')),
        c('profile_sha256', 'TEXT', sha('profile_sha256')), c('created_at', 'INTEGER', integer('created_at')),
        'PRIMARY KEY(token_kind,token_hash)', f'FOREIGN KEY(profile_sha256) REFERENCES {PROFILES}(profile_sha256)']
    result = {}
    unique = {CHALLENGES: [('challenge_id',), ('nonce_sha256',), ('audit_sequence',), ('challenge_sha256',)],
              PROFILES: [('profile_sha256',), ('installation_id','generation','role'), ('generation','role'), ('challenge_id',), ('audit_sequence',)],
              AUTH: [('token_kind','token_hash')]}
    for table, fields in ((CHALLENGES, challenges), (PROFILES, profiles), (AUTH, auth)):
        result[table] = f"CREATE TABLE {table} ({', '.join(fields)})"
        for verb in ('UPDATE','DELETE'):
            name = table+'_immutable_'+verb.lower()
            result[name] = f"CREATE TRIGGER {name} BEFORE {verb} ON {table} BEGIN SELECT RAISE(ABORT,'immutable_runtime_profile_record'); END"
        collision = ' OR '.join('('+' AND '.join(f'{n}=NEW.{n}' for n in key)+')' for key in unique[table])
        name = table+'_immutable_replace'
        result[name] = f"CREATE TRIGGER {name} BEFORE INSERT ON {table} WHEN EXISTS(SELECT 1 FROM {table} WHERE {collision}) BEGIN SELECT RAISE(ABORT,'immutable_runtime_profile_record'); END"

    def guard(name, table, condition):
        result[name] = f"CREATE TRIGGER {name} BEFORE INSERT ON {table} WHEN NOT ({condition}) BEGIN SELECT RAISE(ABORT,'runtime_profile_binding_mismatch'); END"

    guard('recognition_runtime_challenge_binding_guard', CHALLENGES,
        "EXISTS(SELECT 1 FROM recognition_admin_bindings b WHERE b.generation=NEW.source_generation "
        "AND b.generation=(SELECT MAX(generation) FROM recognition_admin_bindings) "
        "AND b.body_sha256=NEW.source_binding_sha256 "
        "AND json_extract(b.body_json,'$.installation_id')=NEW.installation_id "
        "AND json_extract(b.body_json,'$.target_id')=NEW.target_id AND json_extract(b.body_json,'$.owner_id')=NEW.owner_id)")
    guard('recognition_runtime_profile_challenge_guard', PROFILES,
        f"EXISTS(SELECT 1 FROM {CHALLENGES} c JOIN recognition_admin_bindings b ON b.generation=c.source_generation "
        "WHERE c.challenge_id=NEW.challenge_id AND c.source_generation=(SELECT MAX(generation) FROM recognition_admin_bindings) "
        "AND c.source_binding_sha256=b.body_sha256 AND NEW.generation=c.source_generation+1 "
        "AND NEW.installation_id=c.installation_id AND NEW.target_id=c.target_id AND NEW.owner_id=c.owner_id AND NEW.role=c.role "
        "AND NEW.observed_at>=c.issued_at AND NEW.created_at<c.expires_at "
        "AND NEW.target_path=json_extract(b.body_json,'$.target.observation.database') "
        "AND NEW.control_path=json_extract(b.body_json,'$.control_identity.database') "
        "AND NEW.target_inode=(b.body_json -> '$.target.observation.inode') "
        "AND NEW.control_inode=(b.body_json -> '$.control_identity.inode') "
        "AND NEW.target_schema_sha256=json_extract(b.body_json,'$.target.schema_sha256'))")
    # COALESCE makes missing/null JSON members reject rather than SQL NULL suppressing a guard.
    installation_uuid = uuid("json_extract(NEW.body_json,'$.installation_id')")
    target_uuid = uuid("json_extract(NEW.body_json,'$.target_id')")
    guard('recognition_admin_runtime_binding_guard', 'recognition_admin_bindings',
        "COALESCE((json_extract(NEW.body_json,'$.format')='recognition-local-control-v2' "
        "AND NOT EXISTS(SELECT 1 FROM recognition_admin_bindings WHERE json_extract(body_json,'$.format')='recognition-local-control-v3')) OR "
        f"(json_extract(NEW.body_json,'$.format')='{V3}' AND json_type(NEW.body_json,'$.generation')='integer' "
        "AND json_extract(NEW.body_json,'$.generation')=NEW.generation "
        f"AND ({installation_uuid}) AND ({target_uuid}) "
        "AND json_type(NEW.body_json,'$.owner_id')='integer' AND json_extract(NEW.body_json,'$.owner_id')>0 "
        "AND json_extract(NEW.body_json,'$.production_state')='NOT_ACTIVATED' "
        "AND json_type(NEW.body_json,'$.runtime_profile_sha256') IS NOT NULL AND "
        f"(json_type(NEW.body_json,'$.runtime_profile_sha256')='null' OR EXISTS(SELECT 1 FROM {PROFILES} p "
        "WHERE p.profile_sha256=json_extract(NEW.body_json,'$.runtime_profile_sha256') AND p.generation=NEW.generation "
        "AND p.installation_id=json_extract(NEW.body_json,'$.installation_id') AND p.target_id=json_extract(NEW.body_json,'$.target_id') "
        "AND p.owner_id=json_extract(NEW.body_json,'$.owner_id')))),0)")
    guard('recognition_runtime_auth_binding_guard', AUTH,
        f"EXISTS(SELECT 1 FROM {PROFILES} p JOIN recognition_admin_bindings b ON b.generation=p.generation "
        "WHERE p.profile_sha256=NEW.profile_sha256 AND b.generation=(SELECT MAX(generation) FROM recognition_admin_bindings) "
        "AND json_extract(b.body_json,'$.runtime_profile_sha256')=p.profile_sha256 AND "
        "((NEW.token_kind='primary' AND EXISTS(SELECT 1 FROM recognition_admin_primary t WHERE t.token_hash=NEW.token_hash "
        "AND t.generation=p.generation AND t.actor=p.owner_id AND t.revoked=0 AND t.created=NEW.created_at)) OR "
        "(NEW.token_kind='session' AND EXISTS(SELECT 1 FROM recognition_admin_sessions t "
        f"JOIN {AUTH} parent ON parent.token_kind='primary' AND parent.token_hash=t.primary_hash "
        "JOIN recognition_admin_primary primary_proof ON primary_proof.token_hash=t.primary_hash "
        "WHERE t.token_hash=NEW.token_hash AND t.generation=p.generation AND t.actor=p.owner_id AND t.revoked=0 "
        "AND t.created=NEW.created_at AND parent.profile_sha256=p.profile_sha256 "
        "AND primary_proof.revoked=0 AND primary_proof.generation=p.generation AND primary_proof.actor=p.owner_id))))")
    return result


def _check_sha(value):
    require(type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None,
            'runtime_profile_sha_format_mismatch')


def _check_decimal(value, *, inode=False):
    require(type(value) is str and re.fullmatch('0|[1-9][0-9]*', value) is not None
            and (not inode or value != '0'), 'runtime_profile_decimal_format_mismatch')


def check_rows(conn):
    """Supplement SQL constraints with canonical paths, digests and audit links."""
    for table, hash_key in ((CHALLENGES, 'challenge_sha256'), (PROFILES, 'profile_sha256')):
        cursor = conn.execute(f'SELECT * FROM {table}')
        names = [item[0] for item in cursor.description]
        for values in cursor:
            row = dict(zip(names, values))
            for key, value in row.items():
                if key.endswith('_sha256'):
                    _check_sha(value)
            require(digest({k:v for k,v in row.items() if k != hash_key}) == row[hash_key], 'runtime_profile_digest_mismatch')
            for key in ('installation_id', 'target_id', 'challenge_id'):
                require(str(UUID(row[key])) == row[key], 'runtime_profile_uuid_mismatch')
            if table == PROFILES:
                for prefix in ('target', 'control'):
                    _check_decimal(row[prefix+'_device'])
                    _check_decimal(row[prefix+'_inode'], inode=True)
                for key in ('target_path','control_path'):
                    p = Path(row[key])
                    require(p.is_absolute() and str(p.resolve()) == row[key], 'runtime_profile_path_mismatch')
            audit = conn.execute('SELECT body_json FROM recognition_admin_audit WHERE sequence=?', (row['audit_sequence'],)).fetchone()
            require(audit is not None, 'runtime_profile_audit_missing')
            body = load(audit[0])
            moment = row['issued_at'] if table == CHALLENGES else row['created_at']
            require(body.get('subject', {}).get(hash_key) == row[hash_key]
                    and body.get('actor') == row['operator']
                    and int(utc(body['at_utc']).timestamp()) == moment, 'runtime_profile_audit_mismatch')
    for generation, encoded in conn.execute('SELECT generation,body_json FROM recognition_admin_bindings ORDER BY generation'):
        body = load(encoded)
        if body.get('format') != V3:
            continue
        require(type(body.get('generation')) is int and body['generation'] == generation
                and body.get('production_state') == 'NOT_ACTIVATED'
                and 'runtime_profile_sha256' in body, 'runtime_profile_control_binding_mismatch')
        for key in ('installation_id','target_id'):
            require(str(UUID(body[key])) == body[key], 'runtime_profile_uuid_mismatch')
        if body['runtime_profile_sha256'] is not None:
            _check_sha(body['runtime_profile_sha256'])
            p = conn.execute(f'SELECT generation,installation_id,target_id,owner_id FROM {PROFILES} WHERE profile_sha256=?',
                             (body['runtime_profile_sha256'],)).fetchone()
            require(p is not None and tuple(p) == (generation,body['installation_id'],body['target_id'],body['owner_id']),
                    'runtime_profile_control_binding_mismatch')
    # Historical scope rows remain valid after revocation/generation changes;
    # their referenced proof, actor, creation time and generation must still agree.
    for kind, hashed, profile, created in conn.execute(f'SELECT token_kind,token_hash,profile_sha256,created_at FROM {AUTH}'):
        _check_sha(hashed)
        _check_sha(profile)
        table = 'recognition_admin_primary' if kind == 'primary' else 'recognition_admin_sessions'
        proof = conn.execute(f'SELECT generation,actor,created FROM {table} WHERE token_hash=?', (hashed,)).fetchone()
        p = conn.execute(f'SELECT generation,owner_id FROM {PROFILES} WHERE profile_sha256=?', (profile,)).fetchone()
        require(proof is not None and p is not None and tuple(proof) == (p[0],p[1],created), 'runtime_profile_auth_scope_mismatch')
        if kind == 'session':
            parent = conn.execute(f"SELECT a.profile_sha256 FROM {AUTH} a JOIN recognition_admin_sessions s "
                                  "ON a.token_kind='primary' AND a.token_hash=s.primary_hash WHERE s.token_hash=?", (hashed,)).fetchone()
            require(parent is not None and parent[0] == profile, 'runtime_profile_auth_scope_mismatch')
    require(not conn.execute('PRAGMA foreign_key_check').fetchone(), 'runtime_profile_foreign_key_mismatch')

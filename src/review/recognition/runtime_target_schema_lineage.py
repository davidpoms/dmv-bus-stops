"""One closed target-schema successor; original enrollment is never rewritten."""

import base64
import os
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from . import administration as a, event_schema, enrollment
from .rules import canonical, digest
from .trust import fields, load, require


PACKAGE = 'recognition-preactivation-event-foundation-v1'
ACTION = 'runtime_target_event_foundation_completed'
KIND = 'target_event_foundation_completion'
PLAN_FIELDS = tuple(('format package installation_id target_id owner_id generation binding_sha256 profile_sha256 '
    'enrollment_audit_sha256 h0 h1 control_before_sha256 control_after_sha256 definitions_sha256 physical '
    'auth_epoch mfa_epoch owner_key_sha256 target_data_sha256 readiness_sha256 source_audit_sha256 '
    'operator reason created_at_utc deadline_at_utc').split())


def normalized_manifest(objects):
    return digest({name:' '.join(sql.split()) for name, sql in objects.items()})


def source_definitions():
    # This bootstrap edge is deliberately limited to the deployed pre-authority
    # topology. It does not reinterpret arbitrary later migration packages.
    from . import administration_schema, approval_schema, local_readiness, runtime_profile_schema, runtime_execution_claim_schema
    return {**administration_schema.definitions(), **approval_schema.definitions(),
            **local_readiness.definitions(), **runtime_profile_schema.definitions(),
            **runtime_execution_claim_schema.definitions()}


def upgrade_definitions(original):
    """Exact guard successors only. No other predicate is removed or replaced."""
    from . import runtime_execution_claim_schema as claims, runtime_activation_authority_schema as authorities
    result = original.copy()
    for table, path in ((claims.CLAIMS, 'target_snapshot.target.schema_sha256'),
                        (authorities.AUTHORITIES, 'physical_snapshot.target.schema_sha256')):
        name = table+'_scope_guard'
        if name not in result:
            continue
        old = "r.target_schema_sha256=json_extract(NEW.body_json,'$."+path+"')"
        require(result[name].count(old) == 1, 'foundation_original_guard_changed')
        selected = ("(CASE WHEN EXISTS(SELECT 1 FROM recognition_admin_audit f WHERE "
                    f"json_extract(f.body_json,'$.action')='{ACTION}' AND "
                    "json_extract(f.body_json,'$.subject.plan.profile_sha256')=r.profile_sha256) "
                    "THEN (SELECT json_extract(f.body_json,'$.subject.plan.h1') FROM recognition_admin_audit f WHERE "
                    f"json_extract(f.body_json,'$.action')='{ACTION}' AND "
                    "json_extract(f.body_json,'$.subject.plan.profile_sha256')=r.profile_sha256) "
                    "ELSE r.target_schema_sha256 END)")
        result[name] = result[name].replace(old, selected+"=json_extract(NEW.body_json,'$."+path+"')")
    return result


def present(control):
    if not control.execute("SELECT 1 FROM sqlite_master WHERE name='recognition_admin_audit'").fetchone():
        return False
    return bool(control.execute("SELECT 1 FROM recognition_admin_audit WHERE "
        "json_extract(body_json,'$.action')=? OR json_extract(body_json,'$.subject.package')=? LIMIT 1",
        (ACTION, PACKAGE)).fetchone())


def validate_plan(plan):
    from . import runtime_profile_schema as p, runtime_enrollment as codec
    fields(plan, PLAN_FIELDS)
    require(plan['format'] == 'recognition-target-schema-completion-plan-v1'
            and plan['package'] == PACKAGE and type(plan['generation']) is int and plan['generation'] == 5,
            'foundation_plan_scope')
    for key in ('installation_id', 'target_id'):
        from .trust import identity
        identity(plan[key])
    for key in ('owner_id', 'auth_epoch', 'mfa_epoch'):
        codec._integer(plan[key], 1, 2**63-1)
    for key in ('binding_sha256','profile_sha256','enrollment_audit_sha256','h0','h1',
                'control_before_sha256','control_after_sha256','definitions_sha256','owner_key_sha256',
                'target_data_sha256','readiness_sha256','source_audit_sha256'):
        p._check_sha(plan[key])
    require(plan['h0'] != plan['h1'] and plan['definitions_sha256'] == digest(event_schema.definitions()),
            'foundation_package_mismatch')
    require(plan['control_before_sha256'] == normalized_manifest(source_definitions())
            and plan['control_after_sha256'] == normalized_manifest(upgrade_definitions(source_definitions())),
            'foundation_control_package_mismatch')
    codec._text(plan['operator'], 200); codec._text(plan['reason'], 2000)
    from .admin_auth import RECENT_SECONDS
    require(0 < a.timestamp(plan['deadline_at_utc'])-a.timestamp(plan['created_at_utc']) <= RECENT_SECONDS,
            'foundation_plan_lifetime')
    fields(plan['physical'], ('target','control'))
    from .runtime_validation import _physical
    for physical in plan['physical'].values():
        _physical(physical)


def _protected_root(config):
    from . import runtime_production_governance as governance
    root = governance._root(config)
    path = governance.trust_path(config)
    require(path.is_file() and path.stat().st_nlink == 1, 'foundation_approval_root')
    if os.name != 'nt':
        require(path.stat().st_mode & 0o022 == 0 and path.parent.stat().st_mode & 0o022 == 0,
                'foundation_unprotected_root')
    return root


def _signed_history(control, event, subject):
    """Historical approval verification, not a fresh provisioning interface."""
    from . import runtime_production_governance as governance, authorization, admin_auth
    config = SimpleNamespace(control=Path(control.execute('PRAGMA database_list').fetchone()[2]).resolve())
    root = _protected_root(config)
    encoded, signature, plan = subject['approval'], subject['signature'], subject['plan']
    require(type(encoded) is str and len(encoded.encode('utf-8')) <= 65536
            and type(signature) is str and len(signature) == 88, 'foundation_approval_encoding')
    body = load(encoded)
    fields(body, ('format','mandate','installation_id','binding_sha256','holder','subject',
                  'target','control','issued_at_utc','expires_at_utc','approvals'))
    require(canonical(body) == encoded and body['format'] == governance.FORMAT
            and body['mandate'] == root['mandate'] and body['installation_id'] == root['installation_id']
            == plan['installation_id'] and type(root['owner_id']) is int and root['owner_id'] == plan['owner_id'],
            'foundation_approval_root')
    try:
        public = base64.b64decode(root['public_key'], validate=True)
        sig = base64.b64decode(signature, validate=True)
        require(base64.b64encode(public).decode() == root['public_key']
                and base64.b64encode(sig).decode() == signature, 'foundation_approval_encoding')
        Ed25519PublicKey.from_public_bytes(public).verify(sig, governance.DOMAIN+encoded.encode('utf-8'))
    except Exception as error:
        raise authorization.AuthorizationError('foundation_approval_signature') from error
    fields(body['subject'], ('kind','plan'))
    require(body['subject'] == dict(kind=KIND, plan=plan) and body['binding_sha256'] == plan['binding_sha256']
            and body['target'] == plan['physical']['target'] and body['control'] == plan['physical']['control'],
            'foundation_approval_scope')
    fields(body['holder'], ('actor_id','primary_sha256','session_sha256'))
    governance.contract._holder(body['holder'])
    require(body['holder']['actor_id'] == plan['owner_id'], 'foundation_approval_owner')
    expected = authorization.Authorization(target=authorization.Target(**body['target']), environment='production',
        expires_at_utc=body['expires_at_utc'], reference=governance.contract.MANDATE,
        **authorization.migration_binding(PACKAGE, event_schema.definitions()))
    require(body['approvals'] == [asdict(expected)], 'foundation_approval_purpose')
    at, issued, expires = map(a.timestamp, (event['at_utc'], body['issued_at_utc'], body['expires_at_utc']))
    require(a.timestamp(plan['created_at_utc']) <= issued <= at < expires <= issued+admin_auth.RECENT_SECONDS
            and at < a.timestamp(plan['deadline_at_utc']), 'foundation_approval_expired')
    proofs = {}
    for kind, table in (('primary','recognition_admin_primary'), ('session','recognition_admin_sessions')):
        hashed = body['holder'][kind+'_sha256']
        row = control.execute('SELECT * FROM '+table+' WHERE token_hash=?', (hashed,)).fetchone()
        scope = control.execute('SELECT * FROM recognition_runtime_auth_bindings WHERE token_kind=? AND token_hash=?',
                                (kind, hashed)).fetchone()
        require(row is not None and scope is not None and row['actor'] == plan['owner_id']
                and row['generation'] == 5 and row['auth_epoch'] == plan['auth_epoch']
                and row['created'] <= issued <= at < expires <= row['expires']
                and scope['profile_sha256'] == plan['profile_sha256'] and scope['created_at'] == row['created'],
                'foundation_approval_authentication')
        proofs[kind] = row
    require(proofs['session']['primary_hash'] == proofs['primary']['token_hash']
            and proofs['primary']['key_hash'] == plan['owner_key_sha256']
            and proofs['session']['mfa_epoch'] == plan['mfa_epoch'], 'foundation_approval_authentication')


def verify(control):
    from . import runtime_execution_claim_schema as claims, runtime_profile_schema as profiles
    rows = control.execute("SELECT * FROM recognition_admin_audit WHERE json_extract(body_json,'$.action')=? "
                           "OR json_extract(body_json,'$.subject.package')=?", (ACTION, PACKAGE)).fetchall()
    if not rows:
        return None
    require(len(rows) == 1, 'foundation_lineage_ambiguous')
    a._audit_head(control)
    row = rows[0]; event = load(row['body_json']); subject = event['subject']
    fields(subject, ('package','plan','plan_sha256','approval','signature','state'))
    plan = subject['plan']; validate_plan(plan)
    require(event['action'] == ACTION and type(event['actor']) is int and event['actor'] == plan['owner_id']
            and subject['package'] == PACKAGE and subject['state'] == 'CONSUMED'
            and subject['plan_sha256'] == digest(plan) and event['previous_sha256'] == plan['source_audit_sha256'],
            'foundation_lineage_record')
    binding_row = control.execute('SELECT * FROM recognition_admin_bindings WHERE generation=5').fetchone()
    require(binding_row is not None and binding_row['body_sha256'] == plan['binding_sha256'], 'foundation_binding_changed')
    binding = load(binding_row['body_json'])
    require(canonical(binding) == binding_row['body_json'] and digest(binding) == plan['binding_sha256']
            and binding['format'] == profiles.V3, 'foundation_binding_changed')
    profile = control.execute('SELECT * FROM '+profiles.PROFILES+' WHERE profile_sha256=?', (plan['profile_sha256'],)).fetchone()
    require(profile is not None and binding['runtime_profile_sha256'] == plan['profile_sha256']
            and all(binding[key] == profile[key] == plan[key] for key in ('installation_id','target_id','owner_id','generation'))
            and binding['target']['schema_sha256'] == profile['target_schema_sha256'] == plan['h0'],
            'foundation_profile_changed')
    enrolled = control.execute('SELECT body_sha256 FROM recognition_admin_audit WHERE sequence=?',
                               (profile['audit_sequence'],)).fetchone()
    require(enrolled is not None and enrolled[0] == plan['enrollment_audit_sha256']
            and row['sequence'] > profile['audit_sequence'], 'foundation_enrollment_changed')
    for prefix in ('target','control'):
        physical = plan['physical'][prefix]
        require(physical['hostname'] == profile['hostname'] and physical['database'] == profile[prefix+'_path']
                and str(physical['device']) == profile[prefix+'_device']
                and str(physical['inode']) == profile[prefix+'_inode'], 'foundation_physical_changed')
    _signed_history(control, event, subject)
    guard = claims.CLAIMS+'_scope_guard'
    actual = control.execute('SELECT sql FROM sqlite_master WHERE name=?', (guard,)).fetchone()
    require(actual is not None and ' '.join(actual[0].split()) == ' '.join(upgrade_definitions(claims.definitions())[guard].split()),
            'foundation_guard_changed')
    return plan


def expected_schema(control, binding, profile):
    plan = verify(control)
    if plan is not None and plan['profile_sha256'] == profile['profile_sha256']:
        require(digest(binding) == plan['binding_sha256'], 'foundation_binding_changed')
        return plan['h1']
    return profile['target_schema_sha256']


def validate_target(control, target, binding, profile, observed):
    expected = expected_schema(control, binding, profile)
    a.need(binding['target']['schema_sha256'] == profile['target_schema_sha256'] and observed == expected,
           'runtime_profile_schema_mismatch', 503)
    if expected != profile['target_schema_sha256']:
        event_schema.check_schema(target)
        objects = [list(row) for row in target.execute(
            "SELECT type,name,tbl_name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name")
                   if row[1] not in event_schema.definitions()]
        reconstructed = digest(dict(objects=objects, application_id=target.execute('PRAGMA application_id').fetchone()[0],
                                    user_version=target.execute('PRAGMA user_version').fetchone()[0]))
        require(reconstructed == profile['target_schema_sha256'], 'foundation_source_projection_mismatch')


def historical_claim_manifest(control, value):
    plan = verify(control)
    return plan['control_before_sha256'] if plan is not None and value == plan['control_after_sha256'] else value

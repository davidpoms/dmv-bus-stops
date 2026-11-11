"""R28 isolated enrolled owner topology; production approvals use synthetic signatures.

Only test code writes its own deployment public trust input/signs with an
in-memory synthetic key. Production modules never sign or generate a trust root.
"""
from contextlib import contextmanager
from dataclasses import asdict,replace
from datetime import timedelta
from pathlib import Path
import base64
import sqlite3
import tempfile
import time
from unittest.mock import patch
from uuid import uuid4
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat
from src.review.recognition import runtime_production_governance as governance
from src.review.recognition import runtime_finalization_schema_upgrade as upgrade
from src.review.recognition import runtime_authority_lifetime_policy as lifetime
from src.review.recognition import authority,administration_schema as base
from tests import test_recognition_runtime_target_entry_owner as z
from src.review.recognition.rules import canonical,digest
from src.review.recognition.trust import utc,load


@contextmanager
def allocation():
    def writable(suffix=None,prefix=None,dir=None):
        path=Path(__file__).resolve().parents[1]/('recognition-owner-r28-'+uuid4().hex)
        path.mkdir(mode=0o777);return str(path)
    with patch.object(tempfile,'mkdtemp',side_effect=writable):yield


def signed(config,session,primary,subject,key):
    public=base64.b64encode(key.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw)).decode()
    with z.a.connect(config.control) as control:
        binding,_,_=z.v._history(control)
        expires=[control.execute('SELECT expires FROM '+table+' WHERE token_hash=?',(z.a.token_hash(token),)).fetchone()[0]
            for table,token in [('recognition_admin_primary',primary),('recognition_admin_sessions',session)]]
    root=dict(format=governance.FORMAT,mandate=governance.contract.MANDATE,
        installation_id=binding['installation_id'],owner_id=binding['owner_id'],public_key=public)
    governance.trust_path(config).write_text(canonical(root),encoding='utf-8')
    now=z.v._utc_now();end=(utc(now)+timedelta(seconds=600)).strftime('%Y-%m-%dT%H:%M:%SZ')
    assert z.a.timestamp(end)<=min(expires)
    if subject['kind']=='issuer':
        expected=[dict(family='runtime_finalization',permission='governance',action=purpose,
            operation_sha256=digest(subject['intent']),policy_sha256=digest(subject['policy']),population_sha256=None,
            reference=governance.contract.MANDATE) for purpose in ('bind_governance','adopt_policy','appoint_issuer','authorize_issuer')]
        database=config.target
    elif subject['kind']=='journal_install':
        expected=[dict(**z.authorization.migration_binding(upgrade.MIGRATION,upgrade.definitions()),reference=governance.contract.MANDATE)]
        database=config.control
    elif subject['kind']=='revoke_issuer':
        expected=[dict(family='runtime_finalization',permission='governance',action='revoke_issuer',
            operation_sha256=subject['issuer_sha256'],policy_sha256=digest(subject['policy']),population_sha256=None,reference=governance.contract.MANDATE)]
        database=config.target
    else:
        expected=[dict(family='runtime_finalization',permission='inspection',action='inspect_outcome',
            operation_sha256=subject['authority_sha256'],policy_sha256=digest('runtime-finalization-inspection-v1'),population_sha256=None,reference=subject['authority_id'])]
        database=config.target
    approvals=[asdict(z.authorization.Authorization(target=z.authorization.target_identity(database),environment='production',expires_at_utc=end,**b)) for b in expected]
    body=dict(format=governance.FORMAT,mandate=root['mandate'],installation_id=binding['installation_id'],
        binding_sha256=digest(binding),holder=dict(actor_id=binding['owner_id'],primary_sha256=z.a.token_hash(primary),session_sha256=z.a.token_hash(session)),
        subject=subject,target=asdict(z.authorization.target_identity(config.target)),control=asdict(z.authorization.target_identity(config.control)),
        issued_at_utc=now,expires_at_utc=end,approvals=approvals)
    serialized=canonical(body);signature=base64.b64encode(key.sign(governance.DOMAIN+serialized.encode())).decode()
    proof=authority.provision_production_authority(config,session,primary_token=primary,serialized=serialized,signature=signature)
    return dict(proof),body,signature


def transition(test,config,now,package):
    with z.a.connect(config.control) as control:
        binding,profile,_=z.v._history(control)
        head=control.execute('SELECT * FROM recognition_local_activation ORDER BY sequence DESC LIMIT 1').fetchone()
        with z.a.connect(config.target) as target:
            epoch=target.execute('SELECT auth_epoch FROM recognition_local_installation').fetchone()[0]
            after=z.transition._preview(target,migration_id=package.PACKAGE)
        mfa=z.shared._mfa(control,dict(owner_id=binding['owner_id']))
        plan=dict(format=z.s.FORMAT,plan_id=str(uuid4()),installation_id=binding['installation_id'],target_id=binding['target_id'],owner_id=binding['owner_id'],
            source_generation=binding['generation'],source_binding_sha256=digest(binding),source_profile_sha256=profile['profile_sha256'],
            source_auth_epoch=epoch,source_mfa_epoch=mfa,target_schema=dict(before_sha256=binding['target']['schema_sha256'],after_sha256=after,added_definitions_sha256=digest(package.definitions())),
            control_schema_sha256=z.s.claims.manifest(control),migration_id=package.PACKAGE,activation_head=dict(sequence=head['sequence'],event_sha256=head['body_sha256'],state=load(head['body_json'])['state']),
            created_at_utc=z.v._utc_now(),deadline_at_utc=(utc(z.v._utc_now())+timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%SZ'),operator='r28-owner',reason='isolated exact enrolled journal/entry transition')
    backups=[config.target.parent/('r28-backup-'+str(uuid4())+'.db') for _ in range(2)]
    for source,path in zip((config.target,config.control),backups):
        with z.a.connect(source) as src,sqlite3.connect(path) as dst:src.backup(dst)
    generation=binding['generation']+1
    with patch.object(z.a,'target_identity',side_effect=z.authorization.target_identity):
        z.transition.transition(config,plan=plan,plan_sha256=digest(plan),target_backup=backups[0],control_backup=backups[1])
        with z.a.connect(config.control) as control:bound=z.s._binding(control,generation)
        challenge=z.runtime_challenges.issue_challenge(config,expected_generation=generation,installation_id=bound['installation_id'],target_id=bound['target_id'],owner_id=bound['owner_id'],source_binding_sha256=digest(bound),operator='r28-owner',reason='independent synthetic runtime log review',now=z.v._utc_now())
        def observed(subject):
            actual=z.authorization.target_identity(subject);prefix='target' if actual.database==str(config.target) else 'control'
            return replace(actual,hostname=profile['hostname'],device=int(profile[prefix+'_device']),inode=int(profile[prefix+'_inode']))
        with patch.object(z.a,'target_identity',side_effect=observed):
            observation=z.runtime_evidence._collect(config.target,config.control,challenge_id=challenge['challenge']['challenge_id'],challenge_sha256=challenge['challenge']['challenge_sha256'],now=z.v._utc_now())
        review=dict(format=z.enrollment.REVIEW_FORMAT,observations=[observation],selected_observation_sha256=observation['observation_sha256'])
        z.transition.enroll_transition_runtime_profile(config,canonical(review),challenge['nonce'],plan_id=plan['plan_id'],plan_sha256=digest(plan),expected_generation=generation,installation_id=bound['installation_id'],target_id=bound['target_id'],owner_id=bound['owner_id'],source_binding_sha256=digest(bound),challenge_id=challenge['challenge']['challenge_id'],challenge_sha256=challenge['challenge']['challenge_sha256'],approved_review_sha256=digest(review),approved_observation_sha256=observation['observation_sha256'],operator='r28-owner',reason='reviewed same physical runtime',confirm_private_log_review=True,confirm_enroll_runtime_profile=True)
    return plan


def prepare(test, *, lifetime_before=True):
    # Existing fixture provides enrolled owner/schema/auth, but NO journal bootstrap.
    alloc=allocation();alloc.__enter__();test.addCleanup(alloc.__exit__,None,None,None)
    f=z.fixtures.EnrollmentTransitionTests();test.addCleanup(z._cleanup_fixture_tree,f)
    f.setUp();f.migrate();config=f.config;test.config=config
    if lifetime_before:
        with patch.object(z.a,'target_identity',side_effect=z.authorization.target_identity):
            lifetime.migrate(config,expected_generation=3,operator='r28-owner',reason='prospective isolated v2 representation')
    with z.a.connect(config.control) as control:now=[load(z.a._audit_head(control)['body_json'])['at_utc']]
    tick=[time.monotonic_ns()]
    clock=patch.object(z.v,'_utc_now',side_effect=lambda:(utc(now[0])+timedelta(seconds=(time.monotonic_ns()-tick[0])//1_000_000_000)).strftime('%Y-%m-%dT%H:%M:%SZ'));clock.start();test.addCleanup(clock.stop)
    def advance():
        now[0]=(utc(z.v._utc_now())+timedelta(seconds=30)).strftime('%Y-%m-%dT%H:%M:%SZ');tick[0]=time.monotonic_ns()
    # First install the established target-entry package through W/Y.
    transition(test,config,now,z.storage)
    if not lifetime_before:
        with patch.object(z.a,'target_identity',side_effect=z.authorization.target_identity):
            lifetime.migrate(config,expected_generation=5,operator='r28-owner',reason='late representation after completed entry transition')
    advance();primary=z.runtime_auth.record_primary_authentication(config,actor_id=1,reviewer_key='owner-key')
    session=z.runtime_auth.open_admin_session(config,primary,z.totp.independent_code(z.v._utc_now()))
    key=Ed25519PrivateKey.generate()
    proof,_,_=signed(config,session,primary,dict(kind='journal_install'),key)
    with patch.object(z.a,'target_identity',side_effect=z.authorization.target_identity):
        upgrade.migrate_control(config,expected_generation=5,approval=proof['approvals'][0],authority=proof['authority'],operator='r28-owner',reason='signed exact production-path installation')
    transition(test,config,now,upgrade.TargetPackage)
    advance();primary=z.runtime_auth.record_primary_authentication(config,actor_id=1,reviewer_key='owner-key')
    session=z.runtime_auth.open_admin_session(config,primary,z.totp.independent_code(z.v._utc_now()));test.session=session
    with z.a.connect(config.target) as target:
        op=load(target.execute("SELECT body_json FROM recognition_operation_contracts WHERE json_extract(body_json,'$.format')='recognition-local-operation-v2' LIMIT 1").fetchone()[0])
        source=z.events.get_event(target,op['event_id'])['preparation']['request']
    request=dict(request_id=str(uuid4()),family=source['family'],inputs=z.deepcopy(source['inputs']),evaluation_at_utc=source['evaluation_at_utc'],review_reference='fresh production-topology operation',parent_operation_id=None)
    pair=z.runtime_proposals.create_proposal(config,session,request,primary_token=primary);reference=pair['reference']
    advance();step=z.approval_ceremony.issue_step_up(config,session,z.totp.independent_code(z.v._utc_now()),reference,primary_token=primary)
    confirmation=z.approval_ceremony.begin_confirmation(config,session,step['token'],reference,canonical(dict(decision='approve',reason='exact owner operation',confirm=True)),primary_token=primary)
    approved=z.runtime_approvals.issue_approval(config,session,confirmation['token'],canonical(dict(approval_id=str(uuid4()),reference=reference)),primary_token=primary)
    activation=z.activated_fixture.RuntimeActivatedOwnerTests.activate_fixture(test)
    options=dict(primary_token=primary,approval_sha256=approved['approval_sha256'],reference=reference,activation_sha256=digest(activation),reason='owner production-topology validation')
    advance();origin=utc(z.v._utc_now());anchor=time.monotonic_ns();offset=[0];clock.stop()
    live=patch.object(z.v,'_utc_now',side_effect=lambda:(origin+timedelta(seconds=offset[0]+(time.monotonic_ns()-anchor)//1_000_000_000)).strftime('%Y-%m-%dT%H:%M:%SZ'))
    live.start();test.addCleanup(live.stop)
    return config,session,approved['approval']['approval_id'],options,key,offset

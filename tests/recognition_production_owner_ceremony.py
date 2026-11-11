"""Test-only original owner ceremony shared by R28 fault tests and one final run."""
from contextlib import contextmanager
from dataclasses import asdict
from unittest.mock import patch
from src.review.recognition import runtime_finalization as f,runtime_finalization_contract as contract
from src.review.recognition import runtime_activation_authority_issuance as issuer
from src.review.recognition import runtime_activation_authority_schema as source
from src.review.recognition import runtime_schema_package_lineage as lineage
from src.review.recognition import runtime_authority_lifetime_policy as lifetime
from src.review.recognition.rules import canonical,digest
from src.review.recognition.trust import load
from tests import recognition_production_owner_fixture as fixture
from tests.test_recognition_runtime_target_entry_owner import a,v,shared,events,coordinator,metadata,consent,totp


@contextmanager
def ceremony(test,*,prepared=None,stage=None):
    stage=stage or (lambda name:__import__('contextlib').nullcontext())
    with stage('owner topology preparation'):
        config,session,approval_id,options,key,offset=fixture.prepare(test) if prepared is None else prepared
    with a.connect(config.control) as control,a.connect(config.target) as target:
        binding,profile,_=v._history(control);scope=v._identity_snapshot(config,control,target,v._utc_now())
        runtime_target=dict(format='recognition-runtime-operation-target-v1',installation_id=binding['installation_id'],target_id=binding['target_id'],generation=binding['generation'],owner_id=binding['owner_id'],binding_sha256=digest(binding),runtime_profile_sha256=profile['profile_sha256'],auth_epoch=scope['auth_epoch'],mfa_epoch=shared._mfa(control,binding))
        op=load(target.execute('SELECT body_json FROM recognition_operation_contracts WHERE operation_id=?',(options['reference']['operation_id'],)).fetchone()[0])
        manifest=events.get_event(target,op['event_id'])['preparation']['manifest']
    intent=dict(operation_id=op['operation_id'],operation_sha256=digest(op),writer_manifest_sha256=digest(manifest),write_set_sha256=f._write_set(manifest),family=manifest['family'],runtime_target=runtime_target,action=contract.EFFECT)
    policy=dict(format=contract.POLICY,policy_id=contract.ISSUER_ROLE,version=1,action=contract.EFFECT,max_grants=1,lifetime_policy=lineage.V2)
    with stage('signed owner production provisioning'):
        proof,_,_=fixture.signed(config,session,options['primary_token'],dict(kind='issuer',intent=intent,policy=policy),key)
    approvals={x.action:x for x in proof['approvals']}
    offset[0]+=30  # Before authority construction only; distinct fixture MFA counter.
    with stage('issuer governance authorization'):
        receipt=f.authorize_issuer(config,session,totp.independent_code(v._utc_now()),intent,primary_token=options['primary_token'],approvals=approvals,authority=proof['authority'],lifetime_policy=lineage.V2)
    offset[0]+=30
    with stage('fresh original consent'):
        step=consent.issue_step_up(config,session,totp.independent_code(v._utc_now()),approval_id,**options)
        confirm=consent.begin_confirmation(config,session,step['token'],approval_id,canonical(dict(decision='authorize_runtime_execution',reason=options['reason'],confirm=True)),**options)
    real=issuer._body;body=[None]
    def v2_body(state,artifact):
        value=real(state,artifact);assert body[0] is None
        assert state.config==config and state.issuance_phase and state.pending is None
        step=source._artifact(state.control,artifact['step_artifact_sha256'],source.STEP_ACTION,source.STEP)
        deadlines=[state.control.execute('SELECT expires FROM '+table+' WHERE token_hash=?',(value['authentication'][kind+'_sha256'],)).fetchone()[0] for kind,table in [('primary','recognition_admin_primary'),('session','recognition_admin_sessions')]]
        deadlines.extend([a.timestamp(step['expires_at_utc']),a.timestamp(artifact['expires_at_utc'])])
        issued=a.timestamp(value['issued_at_utc']);expires=min(issued+lifetime.seconds(lineage.V2),*deadlines)
        assert expires-issued==300
        value.update(lifetime_policy=lineage.V2,expires_at_utc=consent._time(expires))
        value=source.validate_authority(value);body[0]=value
        test.owner_authority=value
        import time
        test.owner_issued_tick=time.monotonic()
        return value
    with patch.object(issuer,'_body',side_effect=v2_body):
        manager=coordinator.coordinator(config,session,confirm['token'],approval_id,**options,finalization_issuer=receipt['issuer_sha256'])
        with stage('source issuance and coordinator admission'):owner=manager.__enter__()
        try:
            with stage('original attempt creation and final validation'):attempt=owner.create_attempt()
            with stage('protected metadata'):entry=metadata.create_target_entry(attempt)
            yield dict(config=config,session=session,primary=options['primary_token'],options=options,key=key,
                authority=body[0],attempt=attempt,entry=entry,issuer=receipt,policy=policy,offset=offset)
        finally:
            import sys
            with stage('owner cleanup'):manager.__exit__(*sys.exc_info())

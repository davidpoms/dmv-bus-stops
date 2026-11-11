"""R28 child-only owner interruption probe. Never imported as a test runner."""
from contextlib import ExitStack,contextmanager
from dataclasses import replace
from datetime import timedelta
import json,os,sys,time,unittest,sqlite3
from pathlib import Path
from unittest.mock import patch
from cryptography.hazmat.primitives.serialization import Encoding,PrivateFormat,NoEncryption
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from tests.runtime_deadline_harness import MARKER
from tests import recognition_production_owner_ceremony as ceremony
from tests import recognition_production_owner_fixture as fixture
from src.review.recognition import runtime_finalization as f,administration as a,authorization
from src.review.recognition import runtime_validation as v,runtime_production_governance as governance
from src.review.recognition.rules import canonical,digest
from src.review.recognition.trust import utc,load


def emit(value):print(MARKER+json.dumps(value),flush=True)


def inspect(path):
    public=json.loads(Path(path).read_text());root=Path(public['root'])
    assert root.parent==Path(__file__).resolve().parents[1] and root.name.startswith('recognition-owner-r28-')
    saved=json.loads((root/'r28-private-probe.json').read_text())
    config=a.LocalAdministration(*(Path(saved[k]) for k in ('target','control','key_file')))
    assert all(p.parent==root for p in (config.target,config.control,config.key_file))
    key=Ed25519PrivateKey.from_private_bytes((root/'r28-synthetic-signing-key').read_bytes())
    moment=utc(saved['now'])+timedelta(seconds=30);anchor=time.monotonic()
    def identity(subject):
        actual=authorization.target_identity(subject)
        return replace(actual,hostname='synthetic-web',device=actual.device+1)
    with patch.object(v,'_utc_now',side_effect=lambda:(moment+timedelta(seconds=int(time.monotonic()-anchor))).strftime('%Y-%m-%dT%H:%M:%SZ')),patch.object(a,'target_identity',side_effect=identity):
        # Authenticate persisted browser references afresh in the new process;
        # no original registration, attempt or execution right is restored.
        proof,_,_=fixture.signed(config,saved['session'],saved['primary'],dict(kind='inspect',authority_id=saved['authority']['authority_id'],authority_sha256=digest(saved['authority'])),key)
        args=dict(approval=proof['approvals'][0],authority=proof['authority'])
        values=[]
        for _ in range(2):
            try:values.append(dict(f.inspect_outcome(config,saved['authority']['authority_id'],**args)))
            except ValueError as error:
                assert str(error)=='finalization_decision_missing',str(error)
                values.append(dict(state='NO_DECISION',target_commit_verified=False,retry_authorized=False))
        assert values[0]==values[1] and not values[0]['retry_authorized']
        try:f.finalize(object(),object())
        except ValueError:pass
        else:raise AssertionError('restart recreated an executable handoff')
        with a.connect(config.target) as target,a.connect(config.control) as control:
            effect_count=target.execute('SELECT count(*) FROM recognition_private_operations WHERE operation_id=?',(saved['authority']['operation_reference']['writer_manifest_sha256'],)).fetchone()[0]
            witnesses=target.execute('SELECT count(*) FROM '+f.journal.WITNESSES+' WHERE authority_id=?',(saved['authority']['authority_id'],)).fetchone()[0]
            sources=control.execute('SELECT count(*) FROM '+f.source.AUTHORITIES+' WHERE operation_id=?',(saved['authority']['operation_reference']['operation_id'],)).fetchone()[0]
            if effect_count==0:
                assert f.effects._family_snapshot(target)==saved['family_before'],'partial business effect survived rollback'
        assert effect_count==witnesses and sources==1
        emit(dict(kind='inspection',state=values[0]['state'],target_commit_verified=values[0]['target_commit_verified'],retry_authorized=False,effects=effect_count,witnesses=witnesses,sources=sources,root=str(root),fresh_authentication=True,old_handoff_rejected=True))


def execute(scenario,path):
    host=unittest.TestCase();info=None
    @contextmanager
    def progress(name):
        def save():
            config=getattr(host,'config',None)
            Path(path).write_text(json.dumps(dict(root=None if config is None else str(config.target.parent),
                                                 scenario=scenario,phase=name)),encoding='utf-8')
        save()
        try:yield
        finally:save()
    try:
        with ceremony.ceremony(host,stage=progress) as info:
            config=info['config'];root=config.target.parent
            from tests import recognition_authorization_fixture as roots
            roots.workspace_for(config.target)._temporary._finalizer.detach()
            (root/'r28-synthetic-signing-key').write_bytes(info['key'].private_bytes(Encoding.Raw,PrivateFormat.Raw,NoEncryption()))
            with a.connect(config.target) as target:family_before=f.effects._family_snapshot(target)
            def checkpoint():
                saved=dict(target=str(config.target),control=str(config.control),key_file=str(config.key_file),session=info['session'],primary=info['primary'],authority=info['authority'],now=v._utc_now(),family_before=family_before)
                (root/'r28-private-probe.json').write_text(json.dumps(saved),encoding='utf-8')
                Path(path).write_text(json.dumps(dict(root=str(root),scenario=scenario)),encoding='utf-8')
            checkpoint();real=f._commit_target
            def commit(state):
                checkpoint()
                if scenario=='before_commit':os._exit(91)
                real(state);checkpoint()
                if scenario=='after_commit':os._exit(92)
                raise ConnectionError('injected owner response loss after target commit')
            original_append=f._append_event
            def append(state,event):
                if event['state']=='COMPLETED':raise sqlite3.OperationalError('injected control recording failure')
                return original_append(state,event)
            original_start=f._start
            def start(*args):
                result=original_start(*args);checkpoint();os._exit(93)
            with ExitStack() as faults:
                if scenario in ('before_commit','after_commit','lost_response','duplicate','concurrent'):
                    faults.enter_context(patch.object(f,'_commit_target',side_effect=commit))
                if scenario=='control_failure':faults.enter_context(patch.object(f,'_append_event',side_effect=append))
                if scenario=='restart':faults.enter_context(patch.object(f,'_start',side_effect=start))
                if scenario=='concurrent':
                    from concurrent.futures import ThreadPoolExecutor
                    with ThreadPoolExecutor(max_workers=1) as pool:
                        try:pool.submit(f.finalize,info['attempt'],info['entry']).result()
                        except ValueError:pass
                        else:raise AssertionError('foreign thread obtained owner execution')
                if scenario=='revoked':
                    proof,_,_=fixture.signed(config,info['session'],info['primary'],dict(kind='revoke_issuer',issuer_sha256=info['issuer']['issuer_sha256'],policy=info['policy']),info['key'])
                    f.revoke_issuer(config,info['session'],info['issuer']['issuer_sha256'],primary_token=info['primary'],approval=proof['approvals'][0],authority=proof['authority'])
                f.finalize(info['attempt'],info['entry'])
                raise AssertionError('fault scenario unexpectedly returned success')
    except (ConnectionError,OSError,ValueError,sqlite3.Error) as error:
        assert info is not None,'owner preparation/issuance failed before the requested fault'
        if scenario=='revoked':assert str(error)=='finalization_issuer_revoked',str(error)
        elif scenario=='concurrent':assert str(error)=='coordinator_context_invalid',str(error)
        elif scenario in ('lost_response','duplicate'):
            assert str(error)=='injected owner response loss after target commit',str(error)
        elif scenario=='control_failure':assert str(error)=='injected control recording failure',str(error)
        else:raise
        # Reject a second call in the same original process/context too.
        try:f.finalize(info['attempt'],info['entry'])
        except ValueError:pass
        else:raise AssertionError('original owner replay succeeded')
        emit(dict(kind='injected_failure',scenario=scenario,error_class=type(error).__name__,no_usable_result=True,concurrent_rejected=scenario=='concurrent'))


if __name__=='__main__':
    if sys.argv[1]=='inspect':inspect(sys.argv[2])
    else:execute(sys.argv[1],sys.argv[2])

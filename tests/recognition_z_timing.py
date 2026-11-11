"""Opt-in, bounded Z diagnostics. Aggregate timings/counts only; never SQL/data.

Set DMV_RECOGNITION_Z_DIAGNOSTIC_SECONDS (30..240) for the single Z test file.
This instruments existing calls, not their results, clocks or permissions.
"""

from collections import Counter
from contextlib import ExitStack,contextmanager
from functools import wraps
import json
import os
from pathlib import Path
import threading
import time
from unittest.mock import patch


_active=None


def phase(name):
    if _active is not None:
        _active['phase']=name
        _active['phases'].append(dict(phase=name,elapsed_seconds=round(time.perf_counter()-_active['start'],3)))
        print('Z_TIMING_PHASE '+json.dumps(_active['phases'][-1]),flush=True)


def bounded_diagnostic(test):
    @wraps(test)
    def run(*args,**kwargs):
        raw=os.environ.get('DMV_RECOGNITION_Z_DIAGNOSTIC_SECONDS')
        if raw is None:return test(*args,**kwargs)
        budget=int(raw)
        if not 30<=budget<=240:raise ValueError('Z diagnostic budget must be 30..240 seconds')
        from src.review.recognition import administration as a,administration_schema as schema,admin_auth
        from src.review.recognition import runtime_validation as runtime,runtime_enrollment_transition_schema as transitions
        from src.review.recognition import runtime_profile_schema as profiles,runtime_execution_attempt_schema as attempts
        from src.review.recognition import runtime_activation_authority_schema as authorities,runtime_execution_claim_schema as claims
        from src.review.recognition import runtime_execution_coordinator as coordinator,runtime_activation_authority_issuance as issuer
        from src.review.recognition import runtime_scope_validation as scope,local_readiness,dependencies,permanent
        from src.review.recognition import runtime_enrollment as enrollment,runtime_target_entry_owner as metadata
        global _active
        started=time.perf_counter();stats={};stack=[];sql=Counter();pragmas=Counter();stopping=False
        output=Path(__file__).resolve().parents[1]/'.tmp'/'recognition-z-timing.json'
        output.parent.mkdir(exist_ok=True)
        _active=dict(start=started,phase='fixture setup',phases=[],authority_times=None)
        watched=[(runtime,'_history'),(runtime,'_identity_snapshot'),(schema,'check_control'),
            (transitions,'check_rows'),(transitions,'historical_manifest'),(profiles,'check_rows'),
            (attempts,'check_rows'),(authorities,'check_rows'),(claims,'check_rows'),
            (a,'_audit_head'),(enrollment,'parse_review'),(scope,'_view_parts'),(admin_auth,'_session'),
            (local_readiness,'_assess_inventory'),(dependencies,'recheck'),(permanent,'_prepare'),
            (coordinator,'_evaluate'),(coordinator,'_finish'),(issuer,'_subject_for_owner'),
            (issuer,'_persist'),(metadata,'_evaluate')]

        def report(reason):
            now=time.perf_counter()
            records=[dict(component=k,calls=v[0],inclusive_seconds=round(v[1],6),exclusive_seconds=round(v[2],6)) for k,v in list(stats.items())]
            authority_times=_active['authority_times']
            result=dict(reason=reason,elapsed_seconds=round(now-started,3),budget_seconds=budget,
                phase=_active['phase'],phases=list(_active['phases']),
                measured_components=sorted(records,key=lambda r:r['exclusive_seconds'],reverse=True),
                active_components=[dict(component=f[0],elapsed_seconds=round(now-f[1],3)) for f in stack],
                sql_statement_counts=dict(sql),pragma_counts=dict(pragmas),
                metadata_validation_calls=stats.get('runtime_target_entry_owner._evaluate',[0])[0])
            if stopping:
                # Preserve the active boundary when the later finally report
                # runs after normal manager unwinding has emptied the stack.
                if 'interrupted_components' not in _active:
                    _active['interrupted_components']=result['active_components']
                result['interrupted_components']=_active['interrupted_components']
            if authority_times is not None:
                moment=a.timestamp(runtime._utc_now())
                result['authority_lifetime_seconds']=authority_times[1]-authority_times[0]
                result['authority_age_seconds']=moment-authority_times[0]
                result['authority_remaining_seconds']=authority_times[1]-moment
            output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
            print('Z_TIMING_REPORT '+str(output),flush=True)

        def timed(original,label):
            @wraps(original)
            def call(*a,**kw):
                nonlocal stopping
                if not stopping and time.perf_counter()-started>=budget:
                    stopping=True
                    report('bounded diagnostic stopped; no deadline/check modified')
                    raise KeyboardInterrupt('Z diagnostic wall-time budget reached')
                if label=='runtime_execution_coordinator._finish':
                    phase('coordinator final validation: '+('issuance' if a[0].issuance_phase else 'attempt'))
                frame=[label,time.perf_counter(),0.0];stack.append(frame)
                record=stats.setdefault(label,[0,0.0,0.0]);record[0]+=1
                try:
                    result=original(*a,**kw)
                    if label=='runtime_activation_authority_issuance._persist':
                        _active['authority_times']=(
                            authorities._time(result['issued_at_utc']),authorities._time(result['expires_at_utc']))
                    if label=='runtime_execution_coordinator._create_attempt' and os.environ.get('DMV_RECOGNITION_ZR_ONLY')=='1':
                        _active['terminal_reason']='ZR coordinator attempt confirmed; stop before metadata-owner entry'
                        report(_active['terminal_reason'])
                        raise KeyboardInterrupt('ZR diagnostic completed coordinator creation; metadata intentionally not entered')
                    return result
                finally:
                    elapsed=time.perf_counter()-frame[1]
                    stack.pop();record[1]+=elapsed;record[2]+=elapsed-frame[2]
                    if stack:stack[-1][2]+=elapsed
            return call

        original_connect=a.connect
        @contextmanager
        def traced_connect(*a,**kw):
            with original_connect(*a,**kw) as connection:
                def trace(statement):
                    # Count only. Do not retain/log SQL or bound values.
                    words=statement.lstrip().split(None,1)
                    sql[words[0].upper() if words else 'EMPTY']+=1
                    if words and words[0].upper()=='PRAGMA':
                        # PRAGMA name only, never arguments, paths or values.
                        name=words[1].split('(',1)[0].split('=',1)[0].strip().rstrip(';').lower()
                        if name in {'query_only','database_list','foreign_key_check','foreign_keys','journal_mode','synchronous','application_id','user_version','integrity_check','table_info','table_xinfo','index_list','index_info','index_xinfo','foreign_key_list','quick_check'}:
                            pragmas[name]+=1
                        else:pragmas['other']+=1
                connection.set_trace_callback(trace)
                try:yield connection
                finally:connection.set_trace_callback(None)

        # Secondary hard bound: a stuck native call cannot run indefinitely.
        done=threading.Event()
        def watchdog():
            if not done.wait(budget+15):
                try:report('hard diagnostic bound reached in active component')
                finally:os._exit(124)
        threading.Thread(target=watchdog,daemon=True).start()
        try:
            with ExitStack() as patches:
                for module,name in watched:
                    label=module.__name__.rsplit('.',1)[-1]+'.'+name
                    patches.enter_context(patch.object(module,name,timed(getattr(module,name),label)))
                if os.environ.get('DMV_RECOGNITION_ZR_ONLY')=='1':
                    patches.enter_context(patch.object(coordinator,'_create_attempt',timed(coordinator._create_attempt,'runtime_execution_coordinator._create_attempt')))
                patches.enter_context(patch.object(a,'connect',traced_connect))
                return test(*args,**kwargs)
        finally:
            done.set();report(_active.get('terminal_reason', 'bounded stop' if stopping else 'test returned or raised'))
            _active=None
    return run

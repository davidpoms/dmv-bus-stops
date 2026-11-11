"""Protected deployment input + existing authenticated owner, not self-approval.

The independently installed public trust file is an OS-protected deployment
input beside control, never a runtime-created key. No private key is read.
Only exact signed finalization/migration approvals can enter the old Authority
registry interface. Runtime source/issuer consumption remains authoritative.
"""
import base64
from dataclasses import asdict
import os
from pathlib import Path
import threading
from types import MappingProxyType
from weakref import WeakKeyDictionary

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from . import administration as a, runtime_validation as runtime, runtime_auth, admin_auth
from . import authorization, runtime_finalization_contract as contract
from .rules import canonical,digest
from .trust import fields,load,require

FORMAT='recognition-runtime-production-governance-v1'
DOMAIN=b'DMV-runtime-production-governance-v1\x00'
_entries=WeakKeyDictionary()


def trust_path(config):
    return config.control.with_name(config.control.name+'.governance-root.json')


def _root(config):
    path=trust_path(config)
    require(not path.is_symlink() and path.resolve()==path,'production_governance_root_path')
    raw=path.read_text(encoding='utf-8');value=load(raw)
    fields(value,('format','mandate','installation_id','owner_id','public_key'))
    require(raw==canonical(value) and value['format']==FORMAT and value['mandate']==contract.MANDATE,
            'production_governance_root')
    return value


def _verify(config,serialized,signature):
    root=_root(config);body=load(serialized)
    fields(body,('format','mandate','installation_id','binding_sha256','holder','subject',
                 'target','control','issued_at_utc','expires_at_utc','approvals'))
    require(serialized==canonical(body) and body['format']==FORMAT and body['mandate']==root['mandate']
            and body['installation_id']==root['installation_id'],'production_governance_scope')
    try:
        public=base64.b64decode(root['public_key'],validate=True)
        sig=base64.b64decode(signature,validate=True)
        require(base64.b64encode(public).decode()==root['public_key'] and base64.b64encode(sig).decode()==signature,
                'production_governance_encoding')
        Ed25519PublicKey.from_public_bytes(public).verify(sig,DOMAIN+serialized.encode('utf-8'))
    except Exception as error:
        raise authorization.AuthorizationError('production_governance_signature') from error
    now=a.timestamp(runtime._utc_now());issued=a.timestamp(body['issued_at_utc']);expires=a.timestamp(body['expires_at_utc'])
    require(issued<=now<expires<=issued+admin_auth.RECENT_SECONDS,'production_governance_expired')
    contract._holder(body['holder'])
    require(type(root['owner_id']) is int and body['holder']['actor_id']==root['owner_id'],
            'production_governance_owner')
    require(body['target']==asdict(authorization.target_identity(config.target))
            and body['control']==asdict(authorization.target_identity(config.control)),
            'production_governance_physical_identity')
    subject=body['subject'];require(type(subject) is dict,'production_governance_subject')
    approvals=[]
    if subject.get('kind')=='issuer':
        fields(subject,('kind','intent','policy'));contract._intent(subject['intent']);contract._policy(subject['policy'])
        expected=[dict(family='runtime_finalization',permission='governance',action=purpose,
            operation_sha256=digest(subject['intent']),policy_sha256=digest(subject['policy']),
            population_sha256=None,reference=contract.MANDATE) for purpose in
            ('bind_governance','adopt_policy','appoint_issuer','authorize_issuer')]
        target=body['target']
    elif subject.get('kind')=='revoke_issuer':
        fields(subject,('kind','issuer_sha256','policy'))
        from .runtime_profile_schema import _check_sha
        _check_sha(subject['issuer_sha256']);contract._policy(subject['policy'])
        expected=[dict(family='runtime_finalization',permission='governance',action='revoke_issuer',
            operation_sha256=subject['issuer_sha256'],policy_sha256=digest(subject['policy']),
            population_sha256=None,reference=contract.MANDATE)]
        target=body['target']
    elif subject.get('kind')=='inspect':
        fields(subject,('kind','authority_id','authority_sha256'))
        from .trust import identity
        from .runtime_profile_schema import _check_sha
        identity(subject['authority_id']);_check_sha(subject['authority_sha256'])
        expected=[dict(family='runtime_finalization',permission='inspection',action='inspect_outcome',
            operation_sha256=subject['authority_sha256'],policy_sha256=digest('runtime-finalization-inspection-v1'),
            population_sha256=None,reference=subject['authority_id'])]
        target=body['target']
    else:
        from . import runtime_finalization_schema_upgrade as upgrade
        fields(subject,('kind',));require(subject['kind']=='journal_install','production_governance_subject')
        expected=[dict(**authorization.migration_binding(upgrade.MIGRATION,upgrade.definitions()),reference=contract.MANDATE)]
        target=body['control']
    require(type(body['approvals']) is list and len(body['approvals'])==len(expected),'production_governance_approvals')
    for supplied,binding in zip(body['approvals'],expected):
        value=authorization.Authorization(target=authorization.Target(**target),environment='production',
            expires_at_utc=body['expires_at_utc'],**binding)
        require(supplied==asdict(value),'production_governance_approval_scope');approvals.append(value)
    return root,body,tuple(approvals)


def provision(config=None,session=None,*,primary_token=None,serialized=None,signature=None):
    from .authority import Authority
    if type(config) is not a.LocalAdministration:
        raise authorization.AuthorizationError('production_authority_not_provisioned')
    config.paths();root,body,approvals=_verify(config,serialized,signature)
    # Existing 3a/3b kernels independently authenticate current owner/profile.
    # A signed deployment artifact alone is not a login credential or source.
    from . import runtime_finalization as owner
    with owner._reserved(config,session,primary_token,journal_required=False) as state:
        fresh=runtime._utc_now()
        state.view.validate_session(session,primary_token=primary_token)
        control=state.control
        _,_,binding,scope=owner._read_parts(state.context)
        proof=control.execute('SELECT * FROM recognition_admin_sessions WHERE token_hash=?',
                              (a.token_hash(session),)).fetchone()
        require(digest(binding)==body['binding_sha256'] and binding['installation_id']==body['installation_id']
                and scope['owner_id']==root['owner_id']==proof['actor'],'production_governance_binding')
        require(body['holder']==dict(actor_id=proof['actor'],primary_sha256=a.token_hash(primary_token),
                session_sha256=a.token_hash(session)),'production_governance_holder')
        primary=control.execute('SELECT expires FROM recognition_admin_primary WHERE token_hash=?',
                                (a.token_hash(primary_token),)).fetchone()
        require(a.timestamp(body['expires_at_utc'])<=min(primary[0],proof['expires']),'production_governance_credential_clip')
        state.auth_expiries.append((a.timestamp(body['expires_at_utc']),'production_governance_expired'))
        owner._commit_control(state)
    handle=object.__new__(Authority)
    _entries[handle]=dict(config=config,serialized=serialized,signature=signature,root=digest(root),
        approvals=approvals,pid=os.getpid(),thread=threading.current_thread(),
        session=session,primary=primary_token,scope=dict(scope))
    return MappingProxyType(dict(authority=handle,approvals=approvals))


def check_registered(handle,approval):
    from .authority import Authority
    if type(handle) is not Authority:raise authorization.AuthorizationError('provisioned_authority_required')
    entry=_entries.get(handle)
    if entry is None:raise authorization.AuthorizationError('provisioned_authority_required')
    require(entry['pid']==os.getpid() and entry['thread'] is threading.current_thread(),
            'production_authority_original_owner')
    root,body,approvals=_verify(entry['config'],entry['serialized'],entry['signature'])
    require(digest(root)==entry['root'] and approval in approvals and approvals==entry['approvals'],
            'production_authority_scope')
    # Fresh read-only predicates even when verification is called under another
    # owner's writer reservation. Invalid credentials cannot cause this inspector
    # to write reductions; any denial/write attempt fails closed on the RO handle.
    config=entry['config'];now=runtime._utc_now()
    def validate(control,target):
        binding,_,_=runtime._history(control)
        require(digest(binding)==body['binding_sha256'],'production_governance_binding')
        proof=admin_auth._session(control,target,binding,entry['session'],now)[0]
        primary=admin_auth._primary(control,target,binding,entry['primary'],now)
        require(proof['primary_hash']==primary['token_hash'],'production_governance_holder')
        runtime_auth._scope(control,entry['scope'],'primary',primary,now)
        runtime_auth._scope(control,entry['scope'],'session',proof,now)
    from . import runtime_history_validation as history
    current=history._active.get()
    if current is not None:
        state=current['state'];history._key(state)
        require(state.config==config and state.session==entry['session'] and state.primary==entry['primary'],
                'production_authority_original_owner')
        # Same registered evaluation/snapshot: use its existing handles, keeping
        # every live credential query and the R24 history/physical invalidations.
        validate(state.control,state.target)
    else:
        with a.connect(config.control) as control,a.connect(config.target) as target:
            control.execute('BEGIN');target.execute('BEGIN')
            validate(control,target)


def evidence(handle,approval):
    check_registered(handle,approval)
    entry=_entries[handle]
    return dict(serialized=entry['serialized'],signature=entry['signature'],root_sha256=entry['root'])


def verify_evidence(proof,approval):
    fields(proof,('serialized','signature','root_sha256'))
    body=load(proof['serialized'])
    config=a.LocalAdministration(Path(body['target']['database']),Path(body['control']['database']),
                                 Path(body['control']['database']).with_name('unused-inspection-key'))
    root,_,approvals=_verify(config,proof['serialized'],proof['signature'])
    require(digest(root)==proof['root_sha256'] and approval in [asdict(x) for x in approvals],
            'production_governance_audit_provenance')

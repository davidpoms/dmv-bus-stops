"""R24: control-history work sharing inside ONE original live evaluation.

Never spans writes, evaluations, phases, reservations or ceremonies. No auth,
physical observation, admission decision or capability is returned by this scope.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from copy import deepcopy
from functools import wraps
import sqlite3

from . import administration as a
from .rules import canonical
from .trust import require

_active = ContextVar('recognition_one_history_validation', default=None)
_MUTATION = frozenset(getattr(sqlite3,'SQLITE_'+name) for name in (
    'INSERT','UPDATE','DELETE','TRANSACTION','SAVEPOINT','ATTACH','DETACH','ALTER_TABLE',
    'CREATE_INDEX','CREATE_TABLE','CREATE_TEMP_INDEX','CREATE_TEMP_TABLE','CREATE_TRIGGER',
    'CREATE_TEMP_TRIGGER','CREATE_VIEW','CREATE_TEMP_VIEW','CREATE_VTABLE','DROP_INDEX',
    'DROP_TABLE','DROP_TEMP_INDEX','DROP_TEMP_TABLE','DROP_TRIGGER','DROP_TEMP_TRIGGER',
    'DROP_VIEW','DROP_TEMP_VIEW','DROP_VTABLE'))


def note(state,action,first,second):
    if action in _MUTATION or (action==sqlite3.SQLITE_PRAGMA and second is not None
            and first.lower() in ('query_only','foreign_keys','journal_mode','synchronous',
                                  'application_id','user_version','schema_version','writable_schema')):
        invalidate(state)


def record_path(value,kind):
    current=_active.get()
    if current is not None:current['paths'].add((value,kind))


def _owner(context):
    from . import runtime_execution_coordinator as c, runtime_target_entry_owner as m
    from . import runtime_finalization as f
    for cls, resolve in ((c.CoordinatorAdmissionContext,c._state),(m.MetadataContext,m._state),
                         (f.FinalizationContext,f._state)):
        if type(context) is cls:return resolve(context)
    return None


def _key(state):
    require(_owner(state.context) is state,'history_validation_owner_invalid')
    require(type(state.control) is sqlite3.Connection and type(state.target) is sqlite3.Connection
            and state.control.row_factory is sqlite3.Row
            and state.control.in_transaction and state.target.in_transaction,
            'history_validation_reservation_invalid')
    outer=getattr(state,'outer',None)
    scope=(state.context,state.phase_id,state.control,state.target,state.connections,
        state.control_reservation_epoch,state.target_reservation_epoch,
        canonical(dict(state.snapshot)),state.session,state.primary,
        getattr(state,'approval_id',None),getattr(state,'approval_sha256',None),
        canonical(getattr(state,'reference',None)),getattr(state,'activation_sha256',None),
        outer,getattr(outer,'authority_json',None),getattr(outer,'authority_sha256',None),
        state.mfa_epoch,getattr(state,'mode',None))
    return scope,(state.control.total_changes,state.target.total_changes)


@contextmanager
def operation(state):
    if _owner(getattr(state,'context',None)) is not state:
        require(False,'history_validation_owner_invalid')
    current=_active.get()
    if current is not None and current['state'] is state:
        _key(state)
        yield
        return
    # Non-native adapters retain their complete original reads and hooks.
    if type(state.control) is not sqlite3.Connection or type(state.target) is not sqlite3.Connection:
        yield
        return
    token=_active.set(dict(state=state,key=_key(state),value=None,physical=None,paths=set()))
    try:yield
    finally:_active.reset(token)


def evaluate(fn):
    @wraps(fn)
    def evaluated(state,*args,**kwargs):
        with operation(state):return fn(state,*args,**kwargs)
    return evaluated


def subject(fn):
    @wraps(fn)
    def evaluated(context):
        state=_owner(context)
        if state is None:return fn(context)
        with operation(state):return fn(context)
    return evaluated


def invalidate(state):
    current=_active.get()
    if current is not None and current['state'] is state:
        current['value']=current['physical']=None
        current['paths'].clear()


def _physical(state):
    # Z10: a control reservation is NOT filesystem continuity. Reobserve on
    # every consumption; _identity_snapshot also retains its original checks.
    return (a.target_identity(state.config.control),a.target_identity(state.config.target))


def _eligible(control):
    current=_active.get()
    if current is None or control is not current['state'].control:return None
    state=current['state'];key=_key(state)
    if key!=current['key']:
        old=current['key']
        # Only a newly observed mutation count can restart graph validation
        # inside this operation. Scope/resources never silently rebind.
        require(key[0]==old[0],
                'history_validation_scope_changed')
        current.update(key=key,value=None,physical=None,paths=set())
    return current


def read(control):
    current=_eligible(control)
    if current is None or current['value'] is None:return None
    require(_physical(current['state'])==current['physical'],'history_validation_physical_changed')
    # Full graph readers also resolve historical paths (including unselected
    # enrollment observations). Those predicates are filesystem-dependent even
    # when the current DB paths are unchanged. Repeat their original kernels.
    from . import runtime_enrollment as enrollment, runtime_profile_schema as profiles
    for value,kind in tuple(current['paths']):
        if kind=='enrollment':enrollment._path(value)
        else:
            require(kind=='profile','history_validation_path_kind')
            profiles._check_path(value)
    binding,profile,head=current['value']
    # Mutable DATA never aliases the saved value. SQLite Row is immutable.
    return deepcopy(binding),deepcopy(profile),head


def remember(control,value):
    current=_eligible(control)
    if current is not None:
        binding,profile,head=value
        current['value']=(deepcopy(binding),deepcopy(profile),head)
        current['physical']=_physical(current['state'])


def validated(control):
    # Only full current _history success includes the transition graph. Pending
    # state itself is still queried every time by require_no_pending().
    return read(control) is not None

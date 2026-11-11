"""4d-0 point-in-time eligibility DATA, never an execution/writer capability."""

import os
import threading
from types import MappingProxyType
from weakref import WeakKeyDictionary

from . import runtime_operation_contract as contract, runtime_proposal_transaction as owner
from . import runtime_admission_validation as shared
from .rules import canonical, digest
from .trust import identity, load, require


FORMAT = 'recognition-runtime-execution-admission-v1'
_snapshots = WeakKeyDictionary()


def _freeze(value):
    if type(value) is dict:
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if type(value) is list:
        return tuple(_freeze(item) for item in value)
    return value


def _data(snapshot):
    value = _snapshots.get(snapshot) if type(snapshot) is ExecutionAdmission else None
    require(value is not None and value['pid'] == os.getpid()
            and value['thread'] is threading.current_thread(), 'runtime_admission_snapshot_invalid')
    return value


class ExecutionAdmission:
    """Immutable, process/thread-local observation. Never accepted as authority.

    JSON export is archival data only; there is deliberately no import/factory
    accepting detached JSON, dictionaries, timestamps or caller identity claims.
    """

    __slots__ = ('__weakref__',)

    def __new__(cls):
        raise TypeError('runtime_admission_requires_fresh_validation')

    @property
    def canonical_json(self):
        return _data(self)['json']

    @property
    def sha256(self):
        return _data(self)['sha256']

    @property
    def snapshot(self):
        return _freeze(load(self.canonical_json))

    def __reduce_ex__(self, protocol):
        raise TypeError('runtime_admission_cannot_be_restored')


def _collect(context, session_token, primary_token, approval_id, approval_sha256, reference):
    result = shared._assess(shared.proposal_read_view(context), session_token, approval_id,
        approval_sha256, reference, primary_token)
    return load(result.canonical_json)


def _assess(config, session_token, approval_id, approval_sha256, reference, primary_token, *, expected=None):
    identity(approval_id)
    contract.profiles._check_sha(approval_sha256)
    from .runtime_approval_ceremony import _reference
    _reference(reference)
    reference = contract._copy(reference)
    with owner.proposal_transaction(config) as context:
        body = _collect(context, session_token, primary_token, approval_id, approval_sha256, reference)
        if expected is not None:
            shared._compare(body, expected)
        serialized, sha256 = canonical(body), digest(body)
    # Publish only after the owner has performed its final checks and cleanup.
    snapshot = object.__new__(ExecutionAdmission)
    _snapshots[snapshot] = dict(pid=os.getpid(), thread=threading.current_thread(), config=config,
                                json=serialized, sha256=sha256)
    return snapshot


def assess(config, session_token, approval_id, *, approval_sha256, reference, primary_token):
    """Validate exact lookup data against durable state; create no authority."""
    return _assess(config, session_token, approval_id, approval_sha256, reference, primary_token)


def revalidate(snapshot, config, session_token, *, primary_token):
    """New authenticated read of ALL observations. Never a writer-admission API.

    A valid result at T1 does not authorize execution at T2. Future execution
    must independently repeat these and its additional protected gates under
    its own reservations, before creating a claim or acquiring write authority.
    """
    old = _data(snapshot)
    require(config == old['config'], 'runtime_admission_configuration_mismatch')
    body = load(old['json'])
    return _assess(config, session_token, body['approval']['approval_id'], body['approval_sha256'],
                   body['reference'], primary_token, expected=body)

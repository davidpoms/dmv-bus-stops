"""Private fixed-vocabulary diagnostics; never authority or exception text."""

from contextlib import contextmanager
from contextvars import ContextVar
import logging
import os
import sqlite3

from .administration import AdminError
from .qualification import Quarantined
from .rules import canonical
from .trust import TrustError


_scope = ContextVar('recognition_readiness_diagnostic_scope', default=None)
_logger = logging.getLogger(__name__)
_STAGES = frozenset(('readiness_request', 'history_validation', 'runtime_identity_validation',
                     'authentication', 'claim_inspection', 'readiness_inventory',
                     'configuration', 'owner_access', 'foundation_request', 'foundation_plan',
                     'foundation_prerequisites', 'foundation_copy', 'foundation_schema',
                     'foundation_inventory'))
_ADMIN_CLASSES = {code: code for code in (
    'runtime_profile_identity_mismatch', 'runtime_identity_changed', 'runtime_profile_not_enrolled',
    'runtime_profile_enrollment_invalid', 'administrative_clock_rollback',
    'activation_claim_disposition_blocked', 'administrative_session_expired_or_revoked',
    'primary_authentication_required', 'recent_primary_authentication_required')}


def _classification(error):
    if isinstance(error, AdminError):
        return _ADMIN_CLASSES.get(error.code, 'administration_denied') if type(error.code) is str else 'administration_denied'
    if isinstance(error, TrustError):
        return 'trust_validation_failed'
    if isinstance(error, Quarantined):
        return 'recognition_inventory_rejected'
    if isinstance(error, sqlite3.Error):
        return 'database_access_failed'
    if isinstance(error, OSError):
        return 'filesystem_access_failed'
    if isinstance(error, ImportError):
        return 'dependency_import_failed'
    if isinstance(error, ValueError):
        return 'validation_failed'
    return 'unclassified_readiness_failure'


def _record(stage_name, error):
    scope = _scope.get()
    if scope is None or scope['logged']:
        return
    scope['logged'] = True  # One classification, including when the sink fails.
    # Only fixed vocabulary survives for a protected request's error handler.
    scope['diagnostic'] = dict(stage=stage_name, failure_class=_classification(error))
    try:
        record = dict(error='runtime_readiness_failed', stage=stage_name,
                      failure_class=_classification(error), pid=os.getpid())
        _logger.warning('RECOGNITION_READINESS_DIAGNOSTIC %s', canonical(record))
    except Exception:
        pass  # Diagnostics must never replace the original failure.


@contextmanager
def stage(name):
    # All callers supply literals. Never put an arbitrary caller value in a log.
    name = name if name in _STAGES else 'readiness_request'
    try:
        yield
    except Exception as error:
        _record(name, error)
        raise


@contextmanager
def assessment():
    existing = _scope.get()
    if existing is not None:
        yield existing
        return
    scope = dict(logged=False)
    token = _scope.set(scope)
    try:
        with stage('readiness_request'):
            yield scope
    finally:
        _scope.reset(token)

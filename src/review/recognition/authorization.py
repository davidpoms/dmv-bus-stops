"""Approval data and content validation; authority provisioning lives separately.

Writers accept provisioned capabilities, never caller-selected verifiers.
Production provisioning is unavailable. Arbitrary Python/SQL compromise is
outside the application boundary; deployment must enforce OS/process isolation.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re
import socket
import sqlite3

from .qualification import Quarantined
from .rules import digest


@dataclass(frozen=True)
class Target:
    hostname: str
    database: str
    device: int
    inode: int


@dataclass(frozen=True)
class Authorization:
    target: Target
    environment: str
    family: str
    permission: str
    action: str
    operation_sha256: str
    policy_sha256: str
    population_sha256: str | None
    reference: str
    expires_at_utc: str | None = None


class AuthorizationError(Quarantined):
    """Approval failures propagate; never converted to successful processing."""


def _require(condition, code):
    if not condition:
        raise AuthorizationError(code)


def target_identity(database):
    """Observe the actual main database, not a caller's claimed target label."""
    if isinstance(database, sqlite3.Connection):
        databases = database.execute('PRAGMA database_list').fetchall()
        _require(all(row[1] in ('main', 'temp') for row in databases), 'authorization_attached_database')
        database = next(row[2] for row in databases if row[1] == 'main')
        if not database:
            return None  # Only schema rehearsal may use this exemption.
    path = Path(database).resolve(strict=True)
    _require(path.is_file(), 'authorization_target_not_file')
    stat = path.stat()
    return Target(socket.gethostname(), str(path), stat.st_dev, stat.st_ino)


def verify(database, authorization, authority, **expected):
    """Recheck approval on every boundary; no cached approval or token minting."""
    _require(type(authorization) is Authorization, 'authorization_required')
    _require(type(authorization.target) is Target and authorization.target == target_identity(database),
             'authorization_target_mismatch')
    _require(authorization.environment in ('production', 'disposable'), 'authorization_environment_invalid')
    for field in ('family', 'permission', 'action', 'reference'):
        value = getattr(authorization, field)
        _require(isinstance(value, str) and bool(value.strip()), 'authorization_malformed')
    for field in ('operation_sha256', 'policy_sha256', 'population_sha256'):
        value = getattr(authorization, field)
        _require((field == 'population_sha256' and value is None) or
                 (isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value) is not None),
                 'authorization_malformed')
    for field, value in expected.items():
        _require(getattr(authorization, field) == value, 'authorization_' + field + '_mismatch')
    if authorization.expires_at_utc is not None:
        try:
            expiry = datetime.strptime(authorization.expires_at_utc, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
            _require(expiry.strftime('%Y-%m-%dT%H:%M:%SZ') == authorization.expires_at_utc,
                     'authorization_expiry_invalid')
        except (TypeError, ValueError):
            raise AuthorizationError('authorization_expiry_invalid') from None
        _require(datetime.now(timezone.utc) < expiry, 'authorization_expired')
    from .authority import check_authority
    try:
        check_authority(authority, authorization)
    except AuthorizationError:
        raise
    except Quarantined as error:
        raise AuthorizationError('authority_verification_failed') from error


def manifest_binding(manifest):
    live = manifest['format'] == 'live-first-look-operation-v1'
    return dict(family=manifest['family'], permission='issuance',
                action='seal_pending' if live else 'finalize',
                operation_sha256=digest(manifest),
                policy_sha256=manifest['configuration']['policy_sha256'] if live else manifest['rule_sha256'],
                population_sha256=digest({k: manifest[k] for k in ('inputs', 'report', 'identity_history', 'ledger')}),
                reference=manifest['authorization_reference'])


def admission_binding(configuration):
    return dict(family='first_look', permission='capture', action='enqueue',
                operation_sha256=digest(configuration), policy_sha256=configuration['policy_sha256'],
                population_sha256=None, reference=configuration['policy_reference'])


def migration_binding(family, definitions):
    identity = digest(definitions)
    return dict(family=family, permission='migration', action='install',
                operation_sha256=identity, policy_sha256=identity, population_sha256=None)


def verify_migration(conn, family, definitions, authorization=None, authority=None):
    if target_identity(conn) is not None:
        verify(conn, authorization, authority, **migration_binding(family, definitions))

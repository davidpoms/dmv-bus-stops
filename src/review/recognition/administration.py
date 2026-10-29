"""Trusted-operator local installation control. Never authorizes recognition.

Host/DB administrators are trusted. Local generation catches a normal target-only
restore; it is not an independent witness against an unreported in-place restore.
"""

from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
import hashlib
import sqlite3
from uuid import uuid4

from . import administration_schema as schema
from .authorization import target_identity
from .enrollment import _schema as schema_fingerprint
from .rules import canonical, digest
from .trust import load, identity, utc


class AdminError(ValueError):
    def __init__(self, code, status=403):
        super().__init__(code)
        self.code, self.status = code, status


def need(value, code, status=403):
    if not value:
        raise AdminError(code, status)


def timestamp(value):
    return int(utc(value).timestamp())


def token_hash(value):
    need(type(value) is str and 20 <= len(value) <= 256, "administrative_token_required", 401)
    return hashlib.sha256(value.encode()).hexdigest()


@dataclass(frozen=True)
class LocalAdministration:
    target: Path
    control: Path
    key_file: Path

    def paths(self):
        for path in (self.target, self.control, self.key_file):
            need(isinstance(path, Path) and path.is_absolute(), "explicit_admin_paths_required", 503)
        need(self.target.resolve() != self.control.resolve(), "separate_control_store_required", 503)
        need(self.key_file.resolve() not in (self.target.resolve(), self.control.resolve()), "separate_host_key_required", 503)


@contextmanager
def connect(path, *, write=False):
    path = Path(path)
    need(path.is_absolute() and path.is_file() and path.stat().st_nlink == 1, "existing_admin_file_required", 503)
    conn = sqlite3.connect(path.resolve().as_uri() + ("?mode=rw" if write else "?mode=ro"), uri=True)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        if write:
            conn.execute("PRAGMA synchronous=FULL")
        else:
            conn.execute("PRAGMA query_only=ON")
        yield conn
    finally:
        if conn.in_transaction:
            conn.rollback()
        conn.close()


def observe_target(conn):
    return dict(observation=asdict(target_identity(conn)), schema_sha256=schema_fingerprint(conn))


def _binding(conn):
    rows = conn.execute("SELECT generation,body_json,body_sha256 FROM recognition_admin_bindings ORDER BY generation").fetchall()
    need(bool(rows), "installation_not_initialized", 503)
    previous = None
    for index, row in enumerate(rows, 1):
        body = load(row["body_json"])
        need(row["generation"] == index and body["generation"] == index and digest(body) == row["body_sha256"]
             and body["previous_sha256"] == previous, "installation_history_integrity_failure", 503)
        previous = row["body_sha256"]
    # Slice 1 installs storage only. No ordinary administrative/execution path
    # may interpret a v3 binding until its separate runtime contract is implemented.
    need(body.get('format') != 'recognition-local-control-v3', 'runtime_profile_contract_not_enabled', 503)
    return body


def _audit_head(conn):
    previous, last_time, head = None, None, None
    for sequence, row in enumerate(conn.execute("SELECT sequence,body_json,body_sha256 FROM recognition_admin_audit ORDER BY sequence"), 1):
        body = load(row["body_json"])
        need(row["sequence"] == sequence and digest(body) == row["body_sha256"]
             and body["previous_sha256"] == previous and (last_time is None or timestamp(body["at_utc"]) >= last_time),
             "administrative_audit_integrity_failure", 503)
        previous, last_time, head = row["body_sha256"], timestamp(body["at_utc"]), row
    return head


def _audit(conn, action, actor, now, subject=None):
    row = _audit_head(conn)
    if row:
        old = load(row["body_json"])
        need(digest(old) == row["body_sha256"] and timestamp(now) >= timestamp(old["at_utc"]), "admin_clock_or_audit_failure", 503)
    body = dict(action=action, actor=actor, at_utc=now, subject=subject,
                previous_sha256=row["body_sha256"] if row else None)
    conn.execute("INSERT INTO recognition_admin_audit VALUES(?,?,?)",
                 ((row["sequence"] + 1) if row else 1, canonical(body), digest(body)))


def _invalidate(conn):
    conn.execute("UPDATE recognition_admin_primary SET revoked=1")
    conn.execute("UPDATE recognition_admin_sessions SET revoked=1")
    conn.execute("DELETE FROM recognition_admin_stepups")
    conn.execute("UPDATE recognition_admin_confirmations SET used=1")


@contextmanager
def transaction(config, *, lock_target=False):
    need(type(config) is LocalAdministration, "local_administration_required", 503)
    config.paths()
    with connect(config.control, write=True) as control:
        control.execute("BEGIN IMMEDIATE")
        schema.check_control(control)
        _audit_head(control)
        binding = _binding(control)
        need(binding["control_identity"] == asdict(target_identity(config.control)), "control_identity_mismatch", 503)
        with connect(config.target, write=lock_target) as target:
            target.execute("BEGIN IMMEDIATE" if lock_target else "BEGIN")
            _verify(config, control, target, binding)
            yield control, target, binding
            if lock_target:
                # Retain the target writer reservation THROUGH the control commit.
                # No target changes are committed by this context manager.
                control.commit()
        control.commit()


def _verify(config, control, target, binding):
    need(observe_target(target) == binding["target"], "target_identity_or_schema_mismatch", 503)
    schema.check_target(target)
    row = target.execute(f"SELECT * FROM {schema.TARGET_TABLE}").fetchone()
    need(row is not None and row["installation_id"] == binding["installation_id"]
         and row["target_id"] == binding["target_id"] and row["owner_id"] == binding["owner_id"], "installation_target_mismatch", 503)


def get_installation_control(config):
    with transaction(config) as (_, _, binding):
        return dict(binding)


verify_target_control = get_installation_control


def install(config, *, installation_id, owner_id, operator, reason, now):
    """Explicit trusted-host ceremony. No browser/authority provider can call it.

    Target and control commits are separate: retry the SAME installation UUID
    after setup interruption. Neither an incomplete nor complete install enables
    recognition. The caller explicitly creates the empty control file first.
    """
    config.paths()
    from .admin_auth import _cipher
    _cipher(config)  # Explicit setup checks the existing host key, never creates one.
    identity(installation_id)
    need(type(owner_id) is int and owner_id > 0 and bool(operator.strip()) and bool(reason.strip()), "explicit_installation_ceremony_required")
    timestamp(now)
    with connect(config.control, write=True) as control, connect(config.target, write=True) as target:
        control.execute("BEGIN IMMEDIATE")
        schema.install_control(control)
        target.execute("BEGIN IMMEDIATE")
        owner = target.execute("SELECT role,email_verified_at FROM community_reviewers WHERE id=?", (owner_id,)).fetchone()
        need(owner is not None and owner["role"] == "owner" and owner["email_verified_at"], "verified_project_owner_required")
        schema.install_target(target)
        old = target.execute(f"SELECT * FROM {schema.TARGET_TABLE}").fetchone()
        if old:
            need(old["installation_id"] == installation_id and old["owner_id"] == owner_id, "target_already_bound")
            target_id = old["target_id"]
        else:
            target_id = str(uuid4())
            target.execute(f"INSERT INTO {schema.TARGET_TABLE} VALUES(1,?,?,?,1)", (installation_id, target_id, owner_id))
        binding = dict(format="recognition-local-control-v2", installation_id=installation_id, target_id=target_id,
            owner_id=owner_id, generation=1, target=observe_target(target), control_identity=asdict(target_identity(config.control)),
            production_state="NOT_ACTIVATED", at_utc=now, previous_sha256=None)
        if control.execute("SELECT 1 FROM recognition_admin_bindings").fetchone():
            current = _binding(control)
            need(current["installation_id"] == installation_id and current["owner_id"] == owner_id, "control_already_bound")
            _verify(config, control, target, current)
        else:
            control.execute("INSERT INTO recognition_admin_bindings VALUES(1,?,?)", (canonical(binding), digest(binding)))
            control.execute("INSERT INTO recognition_admin_mfa(actor,state,epoch) VALUES(?,'UNENROLLED',1)", (owner_id,))
            _audit(control, "installation_created", operator, now, dict(reason=reason, installation_id=installation_id))
        target.commit()
        control.commit()


def advance_restore_generation(config, *, expected_generation, expected_target_sha256, operator, reason, now):
    """Trusted-host restore/rebind only. Never a web route; never changes old operations."""
    need(bool(operator.strip()) and bool(reason.strip()), "restore_ceremony_required")
    with connect(config.control, write=True) as control, connect(config.target, write=True) as target:
        control.execute("BEGIN IMMEDIATE")
        schema.check_control(control)
        old = _binding(control)
        need(old["control_identity"] == asdict(target_identity(config.control)), "control_identity_mismatch")
        need(type(expected_generation) is int and old["generation"] == expected_generation, "restore_generation_conflict")
        target.execute("BEGIN IMMEDIATE")
        need(digest(observe_target(target)) == expected_target_sha256, "restore_preview_mismatch")
        schema.install_target(target)
        owner = target.execute("SELECT role,email_verified_at FROM community_reviewers WHERE id=?", (old["owner_id"],)).fetchone()
        need(owner is not None and owner["role"] == "owner" and owner["email_verified_at"], "verified_project_owner_required")
        new_id = str(uuid4())
        target.execute(f"DELETE FROM {schema.TARGET_TABLE}")
        target.execute(f"INSERT INTO {schema.TARGET_TABLE} VALUES(1,?,?,?,1)", (old["installation_id"], new_id, old["owner_id"]))
        generation = old["generation"] + 1
        body = dict(old, generation=generation, target_id=new_id, target=observe_target(target),
                    previous_sha256=digest(old), at_utc=now, production_state="NOT_ACTIVATED")
        _invalidate(control)
        if control.execute("SELECT 1 FROM sqlite_master WHERE name='recognition_approvals'").fetchone():
            from .approvals import _invalidate_all
            _invalidate_all(control, operator, now, "restore-generation-advanced")
        control.execute("INSERT INTO recognition_admin_bindings VALUES(?,?,?)", (generation, canonical(body), digest(body)))
        _audit(control, "restore_generation_advanced", operator, now, dict(generation=generation, reason=reason))
        target.commit()
        control.commit()
        return generation


def rebind_filesystem_identity(config, *, expected_generation, expected_target_sha256, operator, reason, now):
    """Trusted-host device-number drift only; no target writes or authority.

    Unlike restore/rebind, inode/path/host/schema/installation must all survive.
    Normal transaction/authorization identity comparisons remain exact.
    """
    need(type(config) is LocalAdministration, "local_administration_required", 503)
    config.paths()
    need(type(operator) is str and bool(operator.strip()) and type(reason) is str and bool(reason.strip()),
         "filesystem_rebind_ceremony_required")
    timestamp(now)
    with connect(config.control, write=True) as control, connect(config.target, write=True) as target:
        control.execute("BEGIN IMMEDIATE")
        schema.check_control(control)
        _audit_head(control)
        old = _binding(control)
        need(type(expected_generation) is int and expected_generation == old["generation"], "filesystem_rebind_generation_conflict")
        need(str(config.control) == old["control_identity"]["database"]
             and str(config.target) == old["target"]["observation"]["database"], "filesystem_rebind_path_mismatch")
        target.execute("BEGIN IMMEDIATE")
        current_control = asdict(target_identity(control))
        current_target = observe_target(target)
        for previous, current in ((old["control_identity"], current_control),
                                  (old["target"]["observation"], current_target["observation"])):
            need(set(previous) == set(current) == {"hostname", "database", "device", "inode"}
                 and all(previous[key] == current[key] for key in ("hostname", "database", "inode")),
                 "filesystem_rebind_non_device_mismatch")
        need(current_control != old["control_identity"] or current_target["observation"] != old["target"]["observation"],
             "filesystem_rebind_device_unchanged")
        need(digest(current_target) == expected_target_sha256, "filesystem_rebind_preview_mismatch")
        need(current_target["schema_sha256"] == old["target"]["schema_sha256"], "filesystem_rebind_schema_mismatch")
        schema.check_target(target)  # Validate existing definitions; never install/migrate.
        row = target.execute(f"SELECT * FROM {schema.TARGET_TABLE}").fetchone()
        need(row is not None and row["installation_id"] == old["installation_id"]
             and row["target_id"] == old["target_id"] and row["owner_id"] == old["owner_id"],
             "installation_target_mismatch")
        owner = target.execute("SELECT role,email_verified_at FROM community_reviewers WHERE id=?", (old["owner_id"],)).fetchone()
        need(owner is not None and owner["role"] == "owner" and owner["email_verified_at"], "verified_project_owner_required")
        generation = old["generation"] + 1
        body = dict(old, generation=generation, control_identity=current_control, target=current_target,
                    previous_sha256=digest(old), at_utc=now, production_state="NOT_ACTIVATED")
        _invalidate(control)
        if control.execute("SELECT 1 FROM sqlite_master WHERE name='recognition_approvals'").fetchone():
            from .approvals import _invalidate_all
            _invalidate_all(control, operator, now, "filesystem-identity-rebound")
        control.execute("INSERT INTO recognition_admin_bindings VALUES(?,?,?)", (generation, canonical(body), digest(body)))
        _audit(control, "filesystem_identity_rebound", operator, now, dict(reason=reason,
            previous_generation=old["generation"], generation=generation, expected_target_sha256=expected_target_sha256,
            old_control_identity=old["control_identity"], control_identity=current_control,
            old_target=old["target"], target=current_target))
        # Detect another observation change before committing the sole modified
        # store. Host operators must quiesce filesystem replacement as well.
        need(asdict(target_identity(control)) == current_control and observe_target(target) == current_target,
             "filesystem_rebind_observation_changed")
        control.commit()  # Keep target writer reservation until this commit ends.
        return generation


def migrate_runtime_profile_contract(config, *, expected_generation, operator, reason, now):
    """Explicit deployment-only v2 -> v3 migration; no profiles or runtime authority.

    The entire ceremony has a savepoint so even a caller catching a failure
    cannot commit partial DDL, revocations, binding or audit changes.
    Repetition with the old generation is rejected; inspect history after lost ACK.
    """
    need(type(operator) is str and bool(operator.strip()) and len(operator) <= 200
         and type(reason) is str and bool(reason.strip()) and len(reason) <= 2000,
         'runtime_migration_ceremony_required')
    timestamp(now)
    with transaction(config, lock_target=True) as (control, target, old):
        need(type(expected_generation) is int and expected_generation == old['generation'], 'runtime_migration_generation_conflict')
        need(old['format'] == 'recognition-local-control-v2', 'runtime_migration_source_format')
        owner = target.execute('SELECT role,email_verified_at FROM community_reviewers WHERE id=?', (old['owner_id'],)).fetchone()
        need(owner is not None and owner['role'] == 'owner' and owner['email_verified_at'], 'verified_project_owner_required')
        if control.execute("SELECT 1 FROM sqlite_master WHERE name='recognition_local_activation'").fetchone():
            from .local_readiness import _state
            need(_state(control, old)['state'] == 'NOT_ACTIVATED', 'runtime_migration_requires_not_activated')
        need(old['production_state'] == 'NOT_ACTIVATED', 'runtime_migration_requires_not_activated')
        control.execute('SAVEPOINT migrate_runtime_contract')
        try:
            schema.install_runtime_extension(control)
            generation = old['generation'] + 1
            body = dict(old, format='recognition-local-control-v3', generation=generation,
                        runtime_profile_sha256=None, previous_sha256=digest(old), at_utc=now,
                        production_state='NOT_ACTIVATED')
            _invalidate(control)
            if control.execute("SELECT 1 FROM sqlite_master WHERE name='recognition_approvals'").fetchone():
                from .approvals import _invalidate_all
                _invalidate_all(control, operator, now, 'runtime-contract-migrated')
            control.execute('INSERT INTO recognition_admin_bindings VALUES(?,?,?)', (generation, canonical(body), digest(body)))
            _audit(control, 'runtime_profile_contract_migrated', operator, now,
                   dict(reason=reason, previous_generation=old['generation'], generation=generation))
            schema.check_control(control)
        except BaseException:
            control.execute('ROLLBACK TO migrate_runtime_contract')
            raise
        finally:
            control.execute('RELEASE migrate_runtime_contract')
        return generation


def reset_mfa(config, *, expected_generation, operator, reason, now):
    """Explicit trusted deployment recovery; email/login alone cannot reset MFA."""
    need(bool(operator.strip()) and bool(reason.strip()), "mfa_reset_ceremony_required")
    with transaction(config) as (control, _, binding):
        need(binding["generation"] == expected_generation, "restore_generation_conflict")
        _invalidate(control)
        control.execute("UPDATE recognition_admin_mfa SET seed_ciphertext=NULL,state='UNENROLLED',epoch=epoch+1,last_counter=-1,pending_primary=NULL,pending_until=NULL")
        _audit(control, "operator_mfa_reset", operator, now, dict(reason=reason))

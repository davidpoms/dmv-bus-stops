"""Authenticated enrollment contracts; only disposable synthetic targets supported.

No production registry, storage attestation, signing, authority or writer integration.
An independent incarnation witness is indispensable: stat/schema alone cannot
detect an in-place restore. The workspace models that external lifecycle signal.
"""

from dataclasses import dataclass
from pathlib import Path
import socket
import sqlite3
import stat
import tempfile
from threading import RLock
from functools import wraps
from uuid import uuid4

from . import trust as t
from .rules import canonical, digest


FORMAT = "recognition-target-enrollment-v1"
DOMAIN = b"DMV-recognition-target-enrollment-v1\x00"
PAYLOAD = {"enrollment_id", "generation", "registry_id", "issuer_id", "key_id", "state",
           "target_type", "target", "issued_at_utc", "provenance", "supersedes"}
TARGET = {"observation", "parent", "host_id", "deployment_id", "incarnation_id", "schema_sha256"}


@dataclass(frozen=True)
class EnrollmentResult:
    """Verification data only; no writer capability or execution permission."""

    state: str
    reason: str
    synthetic_only: bool = True


def validate_reference(reference):
    t.fields(reference, {"enrollment_id", "generation", "record_sha256"})
    t.identity(reference["enrollment_id"])
    t.integer(reference["generation"], 1)
    t.sha(reference["record_sha256"])


def _payload(p):
    t.fields(p, PAYLOAD)
    t.identity(p["enrollment_id"])
    t.integer(p["generation"], 1)
    for field in ("registry_id", "issuer_id", "key_id", "provenance"):
        t.text(p[field])
    t.require(p["state"] == "ENROLLED" and p["target_type"] == "sqlite-main-v1", "invalid_enrollment_state")
    t.utc(p["issued_at_utc"])
    target = p["target"]
    t.fields(target, TARGET)
    t.fields(target["observation"], {"hostname", "database", "device", "inode"})
    for name in ("hostname", "database"):
        t.text(target["observation"][name])
    t.fields(target["parent"], {"path", "device", "inode"})
    t.text(target["parent"]["path"])
    for item in (target["observation"], target["parent"]):
        for field in ("device", "inode"):
            t.require(type(item[field]) is int and 0 <= item[field] <= 2**128-1, "invalid_filesystem_identity")
    for field in ("host_id", "deployment_id"):
        t.text(target[field])
    t.identity(target["incarnation_id"])
    t.sha(target["schema_sha256"])
    if p["supersedes"] is not None:
        validate_reference(p["supersedes"])
        t.require(p["generation"] == p["supersedes"]["generation"] + 1
                  and p["enrollment_id"] != p["supersedes"]["enrollment_id"], "invalid_enrollment_generation")
    else:
        t.require(p["generation"] == 1, "initial_generation_required")


def signing_bytes(payload_json):
    p = t.load(payload_json)
    _payload(p)
    return DOMAIN + canonical(p).encode("utf-8")


def _context(provider):
    t.require(type(provider) is SyntheticEnrollmentWorkspace and not provider._closed,
              "production_enrollment_configuration_unavailable")
    root = provider._root
    observed = root.stat()
    t.require(root.resolve(strict=True) == root and (observed.st_dev, observed.st_ino) == provider._root_identity,
              "enrollment_workspace_changed")
    return t.load(provider._configuration_json)


def verify_record(record_json, *, provider=None):
    """Historical signature/representation only; no current-target claim."""
    config = _context(provider)
    record = t.signed_envelope(record_json, FORMAT)
    p = record["payload"]
    _payload(p)
    t.require(p["registry_id"] == config["registry_id"], "unknown_enrollment_registry")
    t.require(p["issuer_id"] == config["issuer_id"] and p["key_id"] == config["key_id"],
              "unknown_enrolling_authority")
    t.verify_signature(config["public_key"], record["signature"], signing_bytes(canonical(p)))
    return t.VerificationFacts(canonical(record), digest(record))


def reference(record_json, *, provider=None):
    record = verify_record(record_json, provider=provider)
    p = t.load(record.canonical_json)["payload"]
    return dict(enrollment_id=p["enrollment_id"], generation=p["generation"], record_sha256=record.sha256)


def _path(provider, value):
    path = Path(value)
    t.require(path.is_absolute() and path.is_relative_to(provider._root) and path != provider._root,
              "target_outside_disposable_workspace")
    for item in (path, *path.parents):
        observed = item.lstat()
        t.require(not stat.S_ISLNK(observed.st_mode)
                  and not (getattr(observed, "st_file_attributes", 0) & 0x400), "target_alias")
    t.require(path.resolve(strict=True) == path, "target_alias")
    observed = path.stat()
    t.require(stat.S_ISREG(observed.st_mode) and observed.st_nlink == 1, "target_link_or_type_mismatch")
    return path


def _schema(conn):
    databases = conn.execute("PRAGMA database_list").fetchall()
    t.require(len(databases) == 1 and databases[0][1] == "main" and bool(databases[0][2]),
              "attached_or_memory_target")
    objects = [list(row) for row in conn.execute(
        "SELECT type,name,tbl_name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name")]
    return digest(dict(objects=objects, application_id=conn.execute("PRAGMA application_id").fetchone()[0],
                       user_version=conn.execute("PRAGMA user_version").fetchone()[0]))


def _observe(provider, path, expected=None):
    config = _context(provider)
    path = _path(provider, path)
    before, parent = path.stat(), path.parent.stat()
    incarnation = provider._incarnations.get(str(path))
    t.require(incarnation is not None, "independent_incarnation_witness_required")
    identity = dict(observation=dict(hostname=socket.gethostname(), database=str(path),
                                    device=before.st_dev, inode=before.st_ino),
                    parent=dict(path=str(path.parent), device=parent.st_dev, inode=parent.st_ino),
                    host_id=config["host_id"], deployment_id=config["deployment_id"], incarnation_id=incarnation)
    if expected is not None:
        t.require(canonical(identity) == canonical({k: v for k, v in expected.items() if k != "schema_sha256"}),
                  "target_identity_changed")
    conn = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    try:
        conn.execute("PRAGMA query_only=ON")
        conn.execute("BEGIN")
        schema = _schema(conn)
    finally:
        conn.close()
    _context(provider)
    _path(provider, path)
    after, parent_after = path.stat(), path.parent.stat()
    t.require((before.st_dev, before.st_ino, parent.st_dev, parent.st_ino) ==
              (after.st_dev, after.st_ino, parent_after.st_dev, parent_after.st_ino), "target_changed_during_observation")
    t.require(provider._incarnations.get(str(path)) == incarnation, "incarnation_changed_during_observation")
    return dict(identity, schema_sha256=schema)


def _administrative(method):
    @wraps(method)
    def locked(self, *args, **kwargs):
        with self._lock:
            return method(self, *args, **kwargs)
    return locked


class SyntheticEnrollmentWorkspace:
    """Disposable-only administrative registry and external-witness simulator.

    Creates its own root; never adopts an existing target/root. It does not sign.
    Incarnation changes must be reported by the simulated storage administrator;
    this is not automatic detection of unreported in-place filesystem restores.
    """

    def __init__(self, configuration_json):
        config = t.load(configuration_json)
        t.fields(config, {"registry_id", "issuer_id", "key_id", "public_key", "host_id", "deployment_id"})
        for name in config:
            t.text(config[name])
        t.decoded(config["public_key"], 32)
        self._configuration_json = canonical(config)
        self._lock = RLock()
        self._temporary = tempfile.TemporaryDirectory(prefix="recognition-enrollment-synthetic-")
        self._root = Path(self._temporary.name).resolve()
        observed = self._root.stat()
        self._root_identity = (observed.st_dev, observed.st_ino)
        self._closed = False
        self._incarnations = {}
        self._records = {}
        self._current = {}
        self._retired = set()

    @property
    def directory(self):
        return self._root

    def cleanup(self):
        self._closed = True
        self._temporary.cleanup()

    @_administrative
    def establish_incarnation(self, path):
        """Explicit synthetic storage ceremony; not per-operation authorization."""
        _context(self)
        path = _path(self, path)
        t.require(str(path) not in self._incarnations, "incarnation_already_established")
        self._incarnations[str(path)] = str(uuid4())

    @_administrative
    def report_storage_replacement(self, path):
        """Simulate protected storage's signal for restore/replacement, even in-place."""
        _context(self)
        path = _path(self, path)
        t.require(str(path) in self._incarnations, "incarnation_not_established")
        self._incarnations[str(path)] = str(uuid4())

    def payload(self, path, *, enrollment_id, issued_at_utc, provenance, supersedes=None):
        config = _context(self)
        if supersedes is not None:
            validate_reference(supersedes)
        p = dict(enrollment_id=enrollment_id, generation=1 if supersedes is None else supersedes["generation"]+1,
                 registry_id=config["registry_id"], issuer_id=config["issuer_id"], key_id=config["key_id"],
                 state="ENROLLED", target_type="sqlite-main-v1", target=_observe(self, path),
                 issued_at_utc=issued_at_utc, provenance=provenance, supersedes=supersedes)
        _payload(p)
        return canonical(p)

    @_administrative
    def register(self, record_json, *, trusted_now_utc):
        """Explicit synthetic administrative acceptance; immutable records retained."""
        checked = verify_record(record_json, provider=self)
        p = t.load(checked.canonical_json)["payload"]
        t.require(t.utc(p["issued_at_utc"]) <= t.utc(trusted_now_utc), "future_enrollment")
        eid, path = p["enrollment_id"], p["target"]["observation"]["database"]
        if eid in self._records:
            t.require(self._records[eid] == checked.canonical_json, "enrollment_identity_reused")
            return reference(record_json, provider=self)
        t.require(canonical(_observe(self, path)) == canonical(p["target"]), "enrollment_target_mismatch")
        current = self._current.get(path)
        predecessor = p["supersedes"]
        previous_id = predecessor["enrollment_id"] if predecessor is not None else None
        previous_path = None
        if previous_id is None:
            t.require(current is None, "enrollment_predecessor_required")
        else:
            t.require(previous_id in self._records, "unknown_enrollment_predecessor")
            previous_record = self._records[previous_id]
            t.require(predecessor == reference(previous_record, provider=self), "enrollment_predecessor_required")
            previous_path = t.load(previous_record)["payload"]["target"]["observation"]["database"]
            t.require(self._current.get(previous_path) == previous_id and current in (None, previous_id),
                      "enrollment_predecessor_not_current")
        self._records[eid] = checked.canonical_json
        if previous_id is not None:
            self._retired.add(previous_id)
            if previous_path != path:
                del self._current[previous_path]
        self._current[path] = eid
        return reference(record_json, provider=self)

    @_administrative
    def revoke(self, enrollment_id):
        _context(self)
        t.require(enrollment_id in self._records, "unknown_enrollment")
        self._retired.add(enrollment_id)

    def record(self, enrollment_id):
        _context(self)
        t.require(enrollment_id in self._records, "unknown_enrollment")
        return self._records[enrollment_id]


def verify_target(record_json, *, target_path, expected_reference, trusted_now_utc, provider=None):
    """Current synthetic enrollment fact, never authorization or execution admission."""
    try:
        checked = verify_record(record_json, provider=provider)
        validate_reference(expected_reference)
        p = t.load(checked.canonical_json)["payload"]
        t.require(t.utc(p["issued_at_utc"]) <= t.utc(trusted_now_utc), "future_enrollment")
    except (t.TrustError, KeyError, TypeError, ValueError) as error:
        if isinstance(error, t.TrustError) and str(error) in {
            "production_enrollment_configuration_unavailable", "enrollment_workspace_changed"}:
            return EnrollmentResult("VERIFICATION_FAILURE", str(error))
        return EnrollmentResult("INVALID_ENROLLMENT", "invalid_record_or_reference")
    except OSError:
        return EnrollmentResult("VERIFICATION_FAILURE", "registry_unavailable")
    actual_reference = dict(enrollment_id=p["enrollment_id"], generation=p["generation"], record_sha256=checked.sha256)
    if canonical(actual_reference) != canonical(expected_reference):
        return EnrollmentResult("MISMATCH", "enrollment_binding_mismatch")
    eid = p["enrollment_id"]
    if provider._records.get(eid) != checked.canonical_json:
        return EnrollmentResult("INVALID_ENROLLMENT", "enrollment_not_registered")
    if eid in provider._retired or provider._current.get(p["target"]["observation"]["database"]) != eid:
        return EnrollmentResult("REVOKED_OR_SUPERSEDED", "enrollment_not_current")
    try:
        if str(Path(target_path)) != p["target"]["observation"]["database"]:
            return EnrollmentResult("MISMATCH", "target_path_changed")
        observed = _observe(provider, target_path, expected=p["target"])
    except t.TrustError as error:
        if str(error) == "independent_incarnation_witness_required":
            return EnrollmentResult("VERIFICATION_FAILURE", str(error))
        return EnrollmentResult("MISMATCH", str(error))
    except FileNotFoundError:
        return EnrollmentResult("MISMATCH", "target_missing")
    except (OSError, sqlite3.Error):
        return EnrollmentResult("VERIFICATION_FAILURE", "target_observation_failed")
    except (TypeError, ValueError):
        return EnrollmentResult("MISMATCH", "invalid_target_path")
    if canonical(observed) != canonical(p["target"]):
        return EnrollmentResult("MISMATCH", "target_identity_or_schema_changed")
    return EnrollmentResult("MATCH", "synthetic_enrollment_matches")

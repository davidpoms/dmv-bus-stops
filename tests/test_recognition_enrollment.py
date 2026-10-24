"""Disposable target enrollment; no production target, key or registry access."""

import base64
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import FrozenInstanceError
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from src.review.recognition import enrollment as e, trust, authority, authorization, operations
from src.review.recognition.rules import canonical
from src.review.recognition.schema import connection
from tests import test_recognition_operations as op_fixture
from tests import recognition_trust_fixture as trust_fixture
from tests.recognition_authorization_fixture import approval


NOW = "2026-10-19T12:00:00Z"


@contextmanager
def database(path):
    conn = sqlite3.connect(path)
    try:
        with conn:
            yield conn
    finally:
        conn.close()


class EnrollmentTests(unittest.TestCase):
    def setUp(self):
        self.key = Ed25519PrivateKey.generate()
        self.config = dict(registry_id="synthetic-enrollment-registry", issuer_id="synthetic-storage-admin",
            key_id="synthetic-enrollment-key", public_key=base64.b64encode(
                self.key.public_key().public_bytes_raw()).decode(), host_id="synthetic-host", deployment_id="synthetic-deployment")
        self.workspace = e.SyntheticEnrollmentWorkspace(canonical(self.config))
        self.addCleanup(self.workspace.cleanup)
        self.path = self.workspace.directory / "target.sqlite"
        with database(self.path) as conn:
            conn.execute("CREATE TABLE sample(id INTEGER PRIMARY KEY, value TEXT)")
            conn.execute("INSERT INTO sample VALUES(1,'original')")
        self.workspace.establish_incarnation(self.path)
        self.record = self.make_record()
        self.ref = self.workspace.register(self.record, trusted_now_utc=NOW)

    def sign(self, payload, key=None):
        # Independent wire construction; do not use enrollment.signing_bytes().
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
        return canonical(dict(format="recognition-target-enrollment-v1", algorithm="Ed25519", payload=payload,
            signature=base64.b64encode((key or self.key).sign(b"DMV-recognition-target-enrollment-v1\x00" + raw)).decode()))

    def make_record(self, *, supersedes=None, workspace=None, path=None):
        workspace = workspace or self.workspace
        p = trust.load(workspace.payload(path or self.path, enrollment_id=str(uuid4()),
            issued_at_utc=NOW, provenance="synthetic-admin-ceremony", supersedes=supersedes))
        return self.sign(p)

    def verify(self, **overrides):
        args = dict(target_path=self.path, expected_reference=self.ref, trusted_now_utc=NOW, provider=self.workspace)
        return e.verify_target(overrides.pop("record", self.record), **{**args, **overrides})

    def test_match_and_independent_filesystem_and_schema_expectations(self):
        self.assertEqual("MATCH", self.verify().state)
        p = json.loads(self.record)["payload"]
        observed, parent = os.stat(self.path), os.stat(self.path.parent)
        self.assertEqual(dict(hostname=socket.gethostname(), database=str(self.path), device=observed.st_dev,
                              inode=observed.st_ino), p["target"]["observation"])
        self.assertEqual(dict(path=str(self.path.parent), device=parent.st_dev, inode=parent.st_ino), p["target"]["parent"])
        expected = {"objects": [["table", "sample", "sample", "CREATE TABLE sample(id INTEGER PRIMARY KEY, value TEXT)"]],
                    "application_id": 0, "user_version": 0}
        raw = json.dumps(expected, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), p["target"]["schema_sha256"])
        payload = json.dumps(p, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
        self.assertEqual(b"DMV-recognition-target-enrollment-v1\x00" + payload, e.signing_bytes(canonical(p)))

    def test_normal_writes_and_wal_checkpoint_do_not_change_identity(self):
        conn = sqlite3.connect(self.path)
        try:
            self.assertEqual("wal", conn.execute("PRAGMA journal_mode=WAL").fetchone()[0])
            conn.execute("UPDATE sample SET value='normal write'")
            conn.commit()
            self.assertTrue(Path(str(self.path) + "-wal").exists())
            self.assertEqual("MATCH", self.verify().state)
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            self.assertEqual("MATCH", self.verify().state)
        finally:
            conn.close()
        self.assertEqual("MATCH", self.verify().state)

    def test_real_file_replacement_same_path_is_mismatch(self):
        replacement = self.path.with_name("replacement.sqlite")
        shutil.copyfile(self.path, replacement)
        replacement.replace(self.path)
        self.assertEqual("MISMATCH", self.verify().state)

    def test_invalid_replacement_detected_before_sqlite_read(self):
        replacement = self.path.with_name("invalid-replacement.sqlite")
        replacement.write_bytes(b"not a database")
        replacement.replace(self.path)
        with patch.object(sqlite3, "connect", side_effect=AssertionError("replacement opened")):
            self.assertEqual("MISMATCH", self.verify().state)

    def test_real_parent_directory_replacement_is_mismatch(self):
        directory = self.workspace.directory / "nested"
        directory.mkdir()
        target = directory / "target.sqlite"
        shutil.copyfile(self.path, target)
        self.workspace.establish_incarnation(target)
        record = self.make_record(path=target)
        ref = self.workspace.register(record, trusted_now_utc=NOW)
        directory.rename(self.workspace.directory / "old-directory")
        directory.mkdir()
        shutil.copyfile(self.path, target)
        result = self.verify(record=record, target_path=target, expected_reference=ref)
        self.assertEqual("MISMATCH", result.state)

    def test_different_path_and_missing_target_rejected(self):
        other = self.path.with_name("different.sqlite")
        shutil.copyfile(self.path, other)
        self.workspace.establish_incarnation(other)
        self.assertEqual("MISMATCH", self.verify(target_path=other).state)
        self.path.unlink()
        self.assertEqual("MISMATCH", self.verify().state)

    def test_in_place_restore_requires_external_incarnation_change(self):
        original = self.path.read_bytes()
        before_inode = self.path.stat().st_ino
        with database(self.path) as conn:
            conn.execute("UPDATE sample SET value='later state'")
        # Administrative restore signal comes from outside the replaceable database.
        self.workspace.report_storage_replacement(self.path)
        self.path.write_bytes(original)
        self.assertEqual(before_inode, self.path.stat().st_ino)
        self.assertEqual("MISMATCH", self.verify().state)
        self.assertEqual(self.record, self.workspace.record(self.ref["enrollment_id"]))

    def test_unreported_restore_is_not_claimed_detectable_without_independent_witness(self):
        original = self.path.read_bytes()
        self.path.write_bytes(original)
        # Deliberately demonstrate the local observation limit; this is not production attestation.
        self.assertEqual("MATCH", self.verify().state)
        self.workspace._incarnations.clear()
        self.assertEqual("VERIFICATION_FAILURE", self.verify().state)
        self.assertEqual("VERIFICATION_FAILURE", self.verify(provider=None).state)

    def test_schema_change_and_schema_version_change_invalidate(self):
        with database(self.path) as conn:
            conn.execute("CREATE INDEX sample_value ON sample(value)")
        self.assertEqual("MISMATCH", self.verify().state)
        with database(self.path) as conn:
            conn.execute("DROP INDEX sample_value")
        self.assertEqual("MATCH", self.verify().state)
        with database(self.path) as conn:
            conn.execute("PRAGMA user_version=1")
        self.assertEqual("MISMATCH", self.verify().state)

    def test_relocation_reenrollment_preserves_generation_lineage(self):
        relocated = self.path.with_name("restored-new-path.sqlite")
        shutil.copyfile(self.path, relocated)
        self.workspace.establish_incarnation(relocated)
        record = self.make_record(path=relocated, supersedes=self.ref)
        ref = self.workspace.register(record, trusted_now_utc=NOW)
        self.assertEqual(2, ref["generation"])
        self.assertEqual("REVOKED_OR_SUPERSEDED", self.verify().state)
        self.assertEqual("MATCH", self.verify(record=record, expected_reference=ref, target_path=relocated).state)

    def test_hardlink_alias_rejected_even_on_original_path(self):
        alias = self.path.with_name("hardlink.sqlite")
        os.link(self.path, alias)
        self.assertEqual("MISMATCH", self.verify().state)
        self.assertEqual("MISMATCH", self.verify(target_path=alias).state)

    def test_real_symlink_and_ancestor_alias_rejected_when_supported(self):
        alias = self.workspace.directory / "alias.sqlite"
        try:
            alias.symlink_to(self.path)
        except OSError as error:
            self.skipTest("Real symlink creation unavailable: " + str(error))
        self.assertEqual("MISMATCH", self.verify(target_path=alias).state)
        directory_alias = self.workspace.directory / "alias-directory"
        directory_alias.symlink_to(self.workspace.directory, target_is_directory=True)
        self.assertEqual("MISMATCH", self.verify(target_path=directory_alias / self.path.name).state)

    def test_portable_reparse_alias_guard(self):
        original = Path.lstat
        def lstat(path, *args, **kwargs):
            result = original(path, *args, **kwargs)
            if path == self.path:
                class Reparse:
                    st_mode = result.st_mode
                    st_file_attributes = 0x400
                return Reparse()
            return result
        with patch.object(Path, "lstat", lstat):
            self.assertEqual("MISMATCH", self.verify().state)

    def test_outside_workspace_is_rejected_before_target_stat(self):
        outside = self.workspace.directory.parent / "never-inspect-this.sqlite"
        original = Path.lstat
        def lstat(path, *args, **kwargs):
            if path == outside:
                raise AssertionError("outside target inspected")
            return original(path, *args, **kwargs)
        with patch.object(Path, "lstat", lstat):
            self.assertEqual("MISMATCH", self.verify(target_path=outside).state)

    def test_malformed_signature_mutation_and_future_enrollment(self):
        record = json.loads(self.record)
        record["payload"]["provenance"] = "altered"
        for raw in (None, "{}", canonical(record), self.sign({**record["payload"], "generation": True})):
            # malformed signing input is deliberately independently constructed
            with self.subTest(raw=str(raw)[:30]):
                self.assertEqual("INVALID_ENROLLMENT", self.verify(record=raw).state)
        self.assertEqual("INVALID_ENROLLMENT", self.verify(trusted_now_utc="2026-10-18T12:00:00Z").state)
        record = json.loads(self.record)
        record["format"] = "unsupported"
        self.assertEqual("INVALID_ENROLLMENT", self.verify(record=canonical(record)).state)

    def test_reenrollment_requires_new_identity_generation_and_explicit_predecessor(self):
        newer = self.make_record(supersedes=self.ref)
        newref = self.workspace.register(newer, trusted_now_utc=NOW)
        self.assertEqual(2, newref["generation"])
        self.assertNotEqual(self.ref["enrollment_id"], newref["enrollment_id"])
        self.assertEqual("REVOKED_OR_SUPERSEDED", self.verify().state)
        self.assertEqual("MATCH", self.verify(record=newer, expected_reference=newref).state)
        self.assertEqual("MISMATCH", self.verify(record=newer).state)
        self.assertEqual(self.record, self.workspace.record(self.ref["enrollment_id"]))
        self.assertEqual(self.ref, self.workspace.register(self.record, trusted_now_utc=NOW))
        self.assertEqual("REVOKED_OR_SUPERSEDED", self.verify().state)
        with self.assertRaisesRegex(trust.TrustError, "predecessor"):
            self.workspace.register(self.make_record(), trusted_now_utc=NOW)

    def test_revoked_enrollment_cannot_be_reactivated_by_replay(self):
        self.workspace.revoke(self.ref["enrollment_id"])
        self.workspace.register(self.record, trusted_now_utc=NOW)
        self.assertEqual("REVOKED_OR_SUPERSEDED", self.verify().state)

    def test_same_identity_different_target_or_generation_cannot_replace_history(self):
        p = json.loads(self.record)["payload"]
        p["target"]["deployment_id"] = "other-deployment"
        with self.assertRaisesRegex(trust.TrustError, "identity_reused"):
            self.workspace.register(self.sign(p), trusted_now_utc=NOW)
        p = json.loads(self.record)["payload"]
        p["generation"] = 2
        with self.assertRaises(trust.TrustError):
            self.workspace.register(self.sign(p), trusted_now_utc=NOW)
        self.assertEqual(self.record, self.workspace.record(self.ref["enrollment_id"]))

    def test_attached_connection_rejected(self):
        with database(self.path) as conn:
            conn.execute("ATTACH DATABASE ':memory:' AS extra")
            with self.assertRaisesRegex(trust.TrustError, "attached"):
                e._schema(conn)

    def test_infrastructure_failure_is_temporary_and_records_immutable(self):
        with patch.object(sqlite3, "connect", side_effect=sqlite3.OperationalError("synthetic I/O")):
            self.assertEqual("VERIFICATION_FAILURE", self.verify().state)
        result = self.verify()
        with self.assertRaises(FrozenInstanceError):
            result.state = "EXECUTING"
        self.assertEqual(self.record, self.workspace.record(self.ref["enrollment_id"]))

    def test_incarnation_change_during_observation_is_blocked(self):
        original = e._schema
        def schema(conn):
            result = original(conn)
            self.workspace.report_storage_replacement(self.path)
            return result
        with patch.object(e, "_schema", side_effect=schema):
            self.assertEqual("MISMATCH", self.verify().state)

    def test_no_authority_role_or_provisioning_bypass(self):
        for value in (self.verify(), e.verify_record(self.record, provider=self.workspace), self.ref):
            with self.subTest(value=type(value)), self.assertRaises(authorization.AuthorizationError):
                authorization.verify(self.path, value, self.workspace)
        for provider in ({"role": "owner", "enrolled": True}, lambda: True):
            self.assertEqual("VERIFICATION_FAILURE", self.verify(provider=provider).state)
        with self.assertRaisesRegex(authorization.AuthorizationError, "production_authority_not_provisioned"):
            authority.provision_production_authority()
        self.assertFalse(hasattr(e, "execute"))
        before = self.path.read_bytes()
        self.verify()
        self.assertEqual(before, self.path.read_bytes())

    def test_operation_v2_binds_enrollment_without_rewriting_v1_or_bypassing_ready(self):
        fixture = op_fixture.OperationTests("test_creation_bindings_and_independent_digest")
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        old = fixture.make()
        # Allocate a fresh enrollment root within the existing disposable authority root.
        with patch.object(tempfile, "tempdir", str(fixture.path.parent)):
            workspace = e.SyntheticEnrollmentWorkspace(canonical(self.config))
        self.addCleanup(workspace.cleanup)
        target = workspace.directory / "operation-target.sqlite"
        shutil.copyfile(fixture.path, target)
        fixture.path = target
        workspace.establish_incarnation(target)
        event = fixture.freeze(fixture.create()["preparation_id"])["event"]["event_id"]
        record = self.make_record(workspace=workspace, path=target)
        ref = workspace.register(record, trusted_now_utc=NOW)
        subject = dict(event_id=event, accounting_policy=op_fixture.POLICY, enrollment=ref)
        def create():
            with connection(target, write=True) as conn:
                conn.execute("BEGIN IMMEDIATE")
                result = operations.create_operation(conn, event, op_fixture.POLICY,
                    enrollment_reference=ref, enrollment_provider=workspace, trusted_now_utc=NOW,
                    **approval(target, **operations.binding("create", subject)))
                conn.commit()
                return result
        operation = create()
        self.assertEqual("recognition-operation-contract-v2", operation["envelope"]["format"])
        self.assertEqual(ref, operation["envelope"]["enrollment"])
        self.assertEqual(operation, create())
        self.assertEqual("PREPARED", operation["decisions"][-1]["state"])
        with self.assertRaisesRegex(ValueError, "authorized_assertion_required"):
            fixture.execution(operation, "EXECUTING")
        with connection(target) as conn:
            self.assertEqual(old, operations.get_operation(conn, old["envelope"]["operation_id"]))
        fixture.state(event, "STALE")
        with self.assertRaisesRegex(ValueError, "event_not_ready"):
            fixture.decision(operation, "AUTHORIZED", evidence=op_fixture.AUTH)
        self.assertEqual("MATCH", e.verify_target(record, target_path=target, expected_reference=ref,
            trusted_now_utc=NOW, provider=workspace).state)

    def test_signed_authorization_cannot_cross_enrollment_generations_or_bypass_status(self):
        fixture = trust_fixture.TrustFixture()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        operation = deepcopy(fixture.operation)
        operation.update(format=operations.ENROLLED_CONTRACT, enrollment=self.ref)
        payload = trust.load(trust.authorization_payload(canonical(operation), artifact_id=str(uuid4()),
            authority_id="authority-A", key_id="key-A", registry_id="synthetic-registry",
            issued_at_utc=trust_fixture.ISSUED, expires_at_utc=trust_fixture.EXPIRY))
        artifact = fixture.artifact(payload)
        fixture.historical(artifact, operation_json=canonical(operation))
        with self.assertRaises(trust.TrustError):
            fixture.current(artifact, operation_json=canonical(operation), snapshot_json=None)
        newer = self.make_record(supersedes=self.ref)
        newref = self.workspace.register(newer, trusted_now_utc=NOW)
        altered = {**operation, "enrollment": newref}
        with self.assertRaisesRegex(trust.TrustError, "binding"):
            fixture.historical(artifact, operation_json=canonical(altered))


if __name__ == "__main__":
    unittest.main()

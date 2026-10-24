"""Signed status, deterministic time and restart-persistent disposable checkpoints."""

from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
from uuid import uuid4

from src.review.recognition import status, trust as t
from src.review.recognition.rules import canonical
from tests import recognition_trust_fixture as f


class StatusTests(f.TrustFixture):
    def test_canonical_signed_status_and_signature_only_does_not_update_checkpoint(self):
        expected = b"DMV-recognition-authority-status-v1\x00" + json.dumps(
            self.status_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
        self.assertEqual(expected, status.status_signing_bytes(json.dumps(self.status_payload, indent=2)))
        result = status.verify_status_signature(self.snapshot(), provider=self.provider)
        self.assertEqual("synthetic-registry", json.loads(result.canonical_json)["payload"]["registry_id"])
        self.assertEqual([], self.conn.execute("SELECT * FROM recognition_status_checkpoint").fetchall())
        self.check_status()
        self.assertEqual(1, self.conn.execute("SELECT sequence FROM recognition_status_checkpoint").fetchone()[0])

    def test_default_freshness_strict_48_hour_boundary(self):
        self.assertEqual(172800, self.provider.max_status_age_seconds)
        p = {**self.status_payload, "issued_at_utc": f.offset(-172800)}
        self.check_status(self.snapshot(p), trusted_now_utc=f.offset(-1))
        with self.assertRaisesRegex(t.TrustError, "status_stale"):
            self.check_status(self.snapshot(p))
        with self.assertRaisesRegex(t.TrustError, "status_stale"):
            self.check_status(self.snapshot(p), trusted_now_utc=f.offset(1))
        # An expired-for-current-use snapshot can still have a valid signature.
        status.verify_status_signature(self.snapshot(p), provider=self.provider)

    def test_configurable_freshness_and_invalid_settings(self):
        provider = t.SyntheticTrustProvider(canonical(self.config), max_status_age_seconds=60)
        p = {**self.status_payload, "issued_at_utc": f.offset(-59)}
        self.check_status(self.snapshot(p), provider=provider)
        with self.assertRaisesRegex(t.TrustError, "status_stale"):
            self.check_status(self.snapshot(p), provider=provider, trusted_now_utc=f.offset(1))
        for value in (0, -1, True, 48.0, "48"):
            with self.subTest(value=value), self.assertRaises(t.TrustError):
                t.SyntheticTrustProvider(canonical(self.config), max_status_age_seconds=value)

    def test_expiry_future_issuance_and_malformed_time(self):
        for changes in ({"expires_at_utc": f.NOW}, {"issued_at_utc": f.offset(1)},
                        {"issued_at_utc": f.EXPIRY}, {"expires_at_utc": "not-a-time"}):
            with self.subTest(changes=changes), self.assertRaises(t.TrustError):
                self.check_status(self.snapshot({**self.status_payload, **changes}))
        self.check_status(trusted_now_utc=f.ISSUED)

    def test_missing_invalid_signature_and_unsupported_version_do_not_advance(self):
        snapshot = json.loads(self.snapshot())
        snapshot["payload"]["sequence"] = 99
        invalids = [None, "{}", canonical(snapshot), canonical({**json.loads(self.snapshot()), "format": "v2"})]
        for raw in invalids:
            with self.subTest(raw=str(raw)[:30]), self.assertRaises(t.TrustError):
                status.verify_current_status(raw, checkpoint_conn=self.conn, trusted_now_utc=f.NOW,
                                            provider=self.provider)
        self.assertFalse(self.conn.execute("SELECT * FROM recognition_status_checkpoint").fetchall())

    def test_lower_sequence_conflicting_same_sequence_and_idempotent_identical_snapshot(self):
        snapshot = self.snapshot({**self.status_payload, "sequence": 2})
        first = self.check_status(snapshot)
        self.assertEqual(first, self.check_status(snapshot))
        with self.assertRaisesRegex(t.TrustError, "sequence_rollback"):
            self.check_status()
        p = {**self.status_payload, "sequence": 2, "snapshot_id": str(uuid4())}
        with self.assertRaisesRegex(t.TrustError, "sequence_conflict"):
            self.check_status(self.snapshot(p))
        newer = {**p, "sequence": 3}
        self.check_status(self.snapshot(newer))
        with self.assertRaisesRegex(t.TrustError, "sequence_rollback"):
            self.check_status(snapshot)

    def test_configured_sequence_floor(self):
        provider = t.SyntheticTrustProvider(canonical(self.config), minimum_sequence=5)
        with self.assertRaisesRegex(t.TrustError, "sequence_rollback"):
            self.check_status(provider=provider)
        self.check_status(self.snapshot({**self.status_payload, "sequence": 5}), provider=provider)

    def test_checkpoint_survives_actual_process_restart(self):
        self.check_status(self.snapshot({**self.status_payload, "sequence": 2}))
        self.conn.close()
        code = """
import json, pathlib, sqlite3, sys
from src.review.recognition import status, trust
data = json.load(sys.stdin)
provider = trust.SyntheticTrustProvider(json.dumps(data['config']))
conn = sqlite3.connect(pathlib.Path(data['path']).as_uri() + '?mode=rw', uri=True)
try:
    status.verify_current_status(data['snapshot'], checkpoint_conn=conn,
        trusted_now_utc=data['now'], provider=provider)
    print('ACCEPTED')
except trust.TrustError as error:
    print(str(error))
finally:
    conn.close()
"""
        def restart(snapshot):
            result = subprocess.run([sys.executable, "-B", "-c", code], input=canonical(dict(
                config=self.config, path=str(self.checkpoint_path), snapshot=snapshot, now=f.NOW)),
                text=True, capture_output=True, cwd=Path(__file__).resolve().parents[1], timeout=30)
            self.assertEqual(0, result.returncode, result.stderr)
            return result.stdout.strip()
        self.assertEqual("status_sequence_rollback", restart(self.snapshot()))
        newer = {**self.status_payload, "sequence": 3, "snapshot_id": str(uuid4())}
        self.assertEqual("ACCEPTED", restart(self.snapshot(newer)))
        self.assertEqual("status_sequence_rollback", restart(self.snapshot()))
        self.conn = sqlite3.connect(self.checkpoint_path)
        self.addCleanup(self.conn.close)
        self.assertEqual(3, self.conn.execute("SELECT sequence FROM recognition_status_checkpoint").fetchone()[0])

    def test_clock_rollback_survives_connection_restart(self):
        self.check_status()
        self.conn.close()
        self.conn = sqlite3.connect(self.checkpoint_path)
        self.addCleanup(self.conn.close)
        with self.assertRaisesRegex(t.TrustError, "clock_rollback"):
            self.check_status(trusted_now_utc=f.offset(-1))

    def test_revoked_snapshot_checkpoint_survives_rejected_operation(self):
        revoked = deepcopy(self.status_payload)
        revoked["authorities"][0]["state"] = "REVOKED"
        revoked.update(sequence=2, snapshot_id=str(uuid4()))
        with self.assertRaisesRegex(t.TrustError, "authority_revoked"):
            self.current(snapshot_json=self.snapshot(revoked))
        with self.assertRaisesRegex(t.TrustError, "sequence_rollback"):
            self.check_status()
        self.assertEqual(2, self.conn.execute("SELECT sequence FROM recognition_status_checkpoint").fetchone()[0])

    def test_authority_and_key_revocation_are_separate_and_irreversible(self):
        for field in ("state", "key_state"):
            self.conn.execute("DELETE FROM recognition_status_checkpoint")
            self.conn.commit()
            p = deepcopy(self.status_payload)
            p["authorities"][0][field] = "REVOKED"
            self.check_status(self.snapshot(p))
            with self.assertRaisesRegex(t.TrustError, "revoked"):
                self.current(snapshot_json=self.snapshot(p))
            reenabled = {**self.status_payload, "sequence": 2, "snapshot_id": str(uuid4())}
            with self.assertRaisesRegex(t.TrustError, "reenabled"):
                self.check_status(self.snapshot(reenabled))

    def test_new_authority_can_be_added_without_rewriting_historical_snapshot(self):
        config = deepcopy(self.config)
        config["authority_keys"] = config["authority_keys"][:1]
        provider_a = t.SyntheticTrustProvider(canonical(config))
        old = deepcopy(self.status_payload)
        old["authorities"] = old["authorities"][:1]
        self.check_status(self.snapshot(old), provider=provider_a)
        rotated = deepcopy(self.status_payload)
        rotated.update(sequence=2, snapshot_id=str(uuid4()))
        rotated["authorities"][0]["state"] = "REVOKED"
        self.check_status(self.snapshot(rotated))
        self.historical()

    def test_malformed_conflicting_missing_or_unknown_authorities_and_registry(self):
        original = deepcopy(self.status_payload)
        variants = [{**original, "registry_id": "unknown"}, {**original, "key_id": "unknown"},
                    {**original, "sequence": True}, {**original, "sequence": 0},
                    {**original, "authorities": []}, {**original, "authorities": original["authorities"][:1]},
                    {**original, "authorities": original["authorities"] * 2}]
        for field, value in (("authority_id", "unknown"), ("key_id", "unknown"), ("state", "maybe")):
            p = deepcopy(original)
            p["authorities"][0][field] = value
            variants.append(p)
        for p in variants:
            with self.subTest(payload=p), self.assertRaises(t.TrustError):
                self.check_status(self.snapshot(p))

    def test_checkpoint_is_separate_store_installation_explicit_and_rollback_safe(self):
        self.conn.execute("BEGIN IMMEDIATE")
        status.install_checkpoint(self.conn)
        self.conn.rollback()
        self.conn.execute("CREATE TABLE application_role(role TEXT)")
        self.conn.commit()
        with self.assertRaisesRegex(t.TrustError, "isolated_checkpoint_schema"):
            self.check_status()
        self.conn.execute("DROP TABLE application_role")
        self.conn.commit()
        self.conn.execute("BEGIN IMMEDIATE")
        with self.assertRaisesRegex(t.TrustError, "idle_checkpoint"):
            self.check_status()
        self.conn.rollback()
        # A role in the application database cannot act as checkpoint/trust state.
        with sqlite3.connect(self.fixture.path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            with self.assertRaisesRegex(t.TrustError, "isolated_checkpoint_schema"):
                status.install_checkpoint(conn)
            conn.commit()
            self.assertFalse(conn.execute("SELECT name FROM sqlite_master WHERE name='recognition_status_checkpoint'").fetchall())

    def test_in_memory_checkpoint_cannot_claim_restart_protection(self):
        with sqlite3.connect(":memory:") as conn:
            conn.execute("BEGIN IMMEDIATE")
            with self.assertRaisesRegex(t.TrustError, "file_checkpoint"):
                status.install_checkpoint(conn)
            conn.commit()
            self.assertFalse(conn.execute("SELECT name FROM sqlite_master WHERE name='recognition_status_checkpoint'").fetchall())

    def test_checkpoint_corruption_fails_without_resetting_floor(self):
        self.check_status()
        self.conn.execute("UPDATE recognition_status_checkpoint SET snapshot_sha256=?", ("a"*64,))
        self.conn.commit()
        with self.assertRaisesRegex(t.TrustError, "checkpoint_corrupt"):
            self.check_status(self.snapshot({**self.status_payload, "sequence": 2}))
        self.assertEqual(1, self.conn.execute("SELECT sequence FROM recognition_status_checkpoint").fetchone()[0])

    def test_new_sequence_cannot_reuse_snapshot_identity_or_backdate_status(self):
        self.check_status()
        with self.assertRaisesRegex(t.TrustError, "snapshot_identity_reused"):
            self.check_status(self.snapshot({**self.status_payload, "sequence": 2}))
        p = {**self.status_payload, "sequence": 2, "snapshot_id": str(uuid4()), "issued_at_utc": f.offset(-1, f.ISSUED)}
        with self.assertRaisesRegex(t.TrustError, "issuance_rollback"):
            self.check_status(self.snapshot(p))

    def test_concurrent_acceptance_cannot_lower_durable_floor(self):
        snapshots = [self.snapshot({**self.status_payload, "sequence": n, "snapshot_id": str(uuid4())})
                     for n in (4, 5)]
        def accept(raw):
            conn = sqlite3.connect(self.checkpoint_path)
            try:
                status.verify_current_status(raw, checkpoint_conn=conn, trusted_now_utc=f.NOW,
                                             provider=self.provider)
                return "accepted"
            except t.TrustError as error:
                return str(error)
            finally:
                conn.close()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(accept, snapshots))
        self.assertEqual("accepted", results[1])
        self.assertIn(results[0], ("accepted", "status_sequence_rollback"))
        self.assertEqual(5, self.conn.execute("SELECT sequence FROM recognition_status_checkpoint").fetchone()[0])

    def test_status_required_fields_and_nested_duplicate_json_rejected(self):
        for key in (*status.PAYLOAD_FIELDS, "extra"):
            p = deepcopy(self.status_payload)
            if key == "extra":
                p[key] = True
            else:
                del p[key]
            with self.subTest(key=key), self.assertRaises(t.TrustError):
                self.check_status(self.snapshot(p))
        raw = self.snapshot().replace('"state":', '"state":"REVOKED","state":', 1)
        with self.assertRaisesRegex(t.TrustError, "duplicate_json_key"):
            self.check_status(raw)

"""Production-format contracts verified only with disposable test material."""

import ast
import base64
from copy import deepcopy
from dataclasses import FrozenInstanceError
import hashlib
import importlib
import json
from pathlib import Path
import sqlite3
from unittest.mock import patch

from src.review.recognition import artifacts, authority, authorization, trust as t
from src.review.recognition.rules import canonical
from tests import recognition_trust_fixture as f


class TrustTests(f.TrustFixture):
    def test_canonical_authorization_and_exact_slice3_digest(self):
        p = self.payload
        raw = json.dumps(self.operation, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), p["operation"]["envelope_sha256"])
        expected = b"DMV-recognition-authorization-v1\x00" + json.dumps(
            p, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
        self.assertEqual(expected, t.authorization_signing_bytes(json.dumps(dict(reversed(list(p.items()))), indent=2)))
        result = self.historical()
        self.assertEqual(hashlib.sha256(result.canonical_json.encode()).hexdigest(), result.sha256)
        self.assertEqual(set(self.operation), set(t.OPERATION_FIELDS))

    def test_independent_rfc8032_ed25519_vector(self):
        # RFC 8032 section 7.1, TEST 1: fixed published public key/signature, empty message.
        public = bytes.fromhex("d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a")
        signature = bytes.fromhex("e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555f"
                                  "b8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b")
        t.verify_signature(base64.b64encode(public).decode(), base64.b64encode(signature).decode(), b"")
        with self.assertRaisesRegex(t.TrustError, "signature"):
            t.verify_signature(base64.b64encode(public).decode(), base64.b64encode(signature).decode(), b"x")

    def test_signature_mutation_and_cross_domain_rejected(self):
        value = json.loads(self.artifact())
        value["payload"]["artifact_id"] = "00000000-0000-4000-8000-000000000001"
        with self.assertRaisesRegex(t.TrustError, "signature"):
            self.historical(canonical(value))
        value = json.loads(self.artifact())
        value["signature"] = json.loads(f.signed(self.payload, self.keys["A"], "status"))["signature"]
        with self.assertRaisesRegex(t.TrustError, "signature"):
            self.historical(canonical(value))

    def test_every_operation_binding_changed_in_signed_artifact_rejected(self):
        for key in t.DIRECT_BINDINGS + ["envelope_sha256", "accounting_policy_sha256"]:
            p = deepcopy(self.payload)
            p["operation"][key] = "changed"
            with self.subTest(key=key), self.assertRaisesRegex(t.TrustError, "binding"):
                self.historical(self.artifact(p))

    def test_altered_source_envelope_rejected_without_parallel_operation(self):
        for key, value in (("event_id", "00000000-0000-4000-8000-000000000002"),
                           ("preparation_id", "00000000-0000-4000-8000-000000000003"),
                           ("dependencies_sha256", "a"*64), ("population_sha256", "a"*64),
                           ("target_observation", {}), ("accounting_policy", {}),
                           ("provenance", {}), ("parent_event_id", "different-parent")):
            operation = {**self.operation, key: value}
            with self.subTest(key=key), self.assertRaisesRegex(t.TrustError, "binding"):
                self.historical(operation_json=canonical(operation))
        other = self.fixture.freeze(self.fixture.create()["preparation_id"])["event"]["event_id"]
        revised = self.fixture.make(other)["envelope"]
        self.assertEqual(self.operation["writer_manifest_sha256"], revised["writer_manifest_sha256"])
        with self.assertRaisesRegex(t.TrustError, "binding"):
            self.historical(operation_json=canonical(revised))

    def test_wrong_action_family_rule_and_enrollment_fail(self):
        for key, value in (("action", "seal_pending"), ("family", "explorer"),
                           ("rule_sha256", "a"*64),
                           ("enrollment", {"enrollment_id": "fake", "generation": 1})):
            with self.subTest(key=key), self.assertRaises(t.TrustError):
                self.historical(operation_json=canonical({**self.operation, key: value}))

    def test_binding_equality_is_type_exact_for_nested_target_values(self):
        operation = deepcopy(self.operation)
        operation["target_observation"]["device"] = 0
        p = deepcopy(self.payload)
        p["operation"] = t.operation_binding(canonical(operation))
        p["operation"]["target_observation"]["device"] = False
        with self.assertRaisesRegex(t.TrustError, "binding"):
            self.historical(self.artifact(p), operation_json=canonical(operation))

    def test_unknown_authority_key_registry_and_grant_fail(self):
        for key, value in (("authority_id", "unknown"), ("key_id", "unknown"), ("registry_id", "unknown")):
            p = {**self.payload, key: value}
            with self.subTest(key=key), self.assertRaises(t.TrustError):
                self.historical(self.artifact(p))
        config = deepcopy(self.config)
        config["authority_keys"][0]["grants"] = [dict(family="geography_steward", action="finalize")]
        with self.assertRaisesRegex(t.TrustError, "grant"):
            self.historical(provider=t.SyntheticTrustProvider(canonical(config)))

    def test_expiry_future_issuance_and_exact_time_boundaries(self):
        self.current(trusted_now_utc=f.ISSUED)
        for now in (f.offset(-1, f.ISSUED), f.EXPIRY):
            with self.subTest(now=now), self.assertRaisesRegex(t.TrustError, "authorization_not_current"):
                self.current(trusted_now_utc=now)
        # Expired authorization remains a historical signature fact.
        self.historical()
        p = {**self.payload, "expires_at_utc": f.ISSUED}
        with self.assertRaisesRegex(t.TrustError, "interval"):
            self.historical(self.artifact(p))

    def test_malformed_unknown_fields_versions_types_and_duplicate_keys(self):
        original = json.loads(self.artifact())
        for location in ("envelope", "payload"):
            keys = original.keys() if location == "envelope" else original["payload"].keys()
            for key in (*keys, "unexpected"):
                value = deepcopy(original)
                target = value if location == "envelope" else value["payload"]
                if key == "unexpected":
                    target[key] = True
                else:
                    del target[key]
                with self.subTest(location=location, key=key), self.assertRaises(t.TrustError):
                    self.historical(canonical(value))
        for raw in (None, {}, "null", "[]", "{", canonical({**original, "format": "v2"}),
                    canonical({**original, "algorithm": "none"}),
                    self.artifact().replace('"artifact_id":', '"artifact_id":"x","artifact_id":', 1),
                    self.artifact().replace('"state":', '"state":"x","state":', 1) + "x"):
            with self.subTest(raw=str(raw)[:30]), self.assertRaises(t.TrustError):
                t.verify_historical_authorization(raw, operation_json=self.operation_json, provider=self.provider)
        for number in ("NaN", "Infinity", "1.0", "1e999"):
            with self.subTest(number=number), self.assertRaises(t.TrustError):
                t.load('{"nested":{"value":' + number + '}}')

    def test_authorization_and_status_are_independent_required_facts(self):
        self.historical()
        for value in (None, "{}", self.artifact()):
            with self.subTest(value=str(value)[:20]), self.assertRaises(t.TrustError):
                self.current(snapshot_json=value)
        self.check_status()
        with self.assertRaises(t.TrustError):
            self.current("{}")

    def test_rotation_preserves_history_revokes_a_and_allows_b(self):
        old_artifact = self.artifact()
        original_bytes = old_artifact.encode()
        self.current(old_artifact)
        status = deepcopy(self.status_payload)
        status.update(sequence=2, snapshot_id="00000000-0000-4000-8000-000000000004")
        status["authorities"][0].update(state="REVOKED", key_state="REVOKED")
        with self.assertRaisesRegex(t.TrustError, "revoked"):
            self.current(old_artifact, snapshot_json=self.snapshot(status))
        self.historical(old_artifact)
        p = {**self.payload, "authority_id": "authority-B", "key_id": "key-B",
             "artifact_id": "00000000-0000-4000-8000-000000000005"}
        self.current(self.artifact(p, name="B"), snapshot_json=self.snapshot(status))
        self.assertEqual(original_bytes, old_artifact.encode())
        with self.assertRaisesRegex(t.TrustError, "revoked"):
            self.current(self.artifact({**self.payload, "artifact_id": p["artifact_id"]}), snapshot_json=self.snapshot(status))

    def test_no_provider_callback_role_or_valid_test_key_becomes_authority(self):
        for provider in (None, {"role": "owner"}, lambda: True, object()):
            with self.subTest(provider=type(provider)), self.assertRaisesRegex(t.TrustError, "unavailable"):
                self.historical(provider=provider)
        result = self.current()
        with self.assertRaises(FrozenInstanceError):
            result.sha256 = "changed"
        with self.assertRaisesRegex(authorization.AuthorizationError, "authorization_required"):
            authorization.verify(self.fixture.path, result, self.provider)
        with self.assertRaisesRegex(authorization.AuthorizationError, "production_authority_not_provisioned"):
            authority.provision_production_authority()
        # Old synthetic artifact verifier also remains unusable as the new provider.
        self.assertIn("recognition-synthetic-approval-v1", artifacts.FORMAT)
        with self.assertRaises(t.TrustError):
            self.historical(provider=object.__new__(artifacts.SyntheticArtifactVerifier))

    def test_imports_no_sql_no_signing_and_no_writer_or_explorer_integration(self):
        with patch.object(sqlite3, "connect", side_effect=AssertionError("opened SQLite")):
            importlib.reload(t)
            self.provider = t.SyntheticTrustProvider(canonical(self.config))
            self.historical()
        root = Path(__file__).resolve().parents[1]
        for relative in ("src/api/app.py", "src/review/recognition/permanent.py",
                         "src/review/recognition/live_first_looks.py", "src/review/recognition/processing.py"):
            tree = ast.parse((root / relative).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    self.assertFalse(node.module and node.module.split(".")[-1] in {"trust", "status", "artifacts"})
                    if node.module and "recognition" in node.module:
                        self.assertFalse({"trust", "status", "artifacts"} & {a.name for a in node.names})
                elif isinstance(node, ast.Import):
                    self.assertFalse(any(a.name.split(".")[-1] in {"trust", "status", "artifacts"}
                                         for a in node.names))
        for module in ("trust.py", "status.py"):
            source = (root / "src/review/recognition" / module).read_text()
            tree = ast.parse(source)
            calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
            self.assertFalse(any(isinstance(n.func, ast.Attribute) and n.func.attr in
                                 {"sign", "generate", "finalize", "seal_pending"} for n in calls))

    def test_verification_never_mutates_operation_target_or_explorer(self):
        before = self.fixture.path.read_bytes()
        self.current()
        self.historical()
        self.assertEqual(before, self.fixture.path.read_bytes())
        self.assertNotEqual(self.fixture.path, self.checkpoint_path)

    def test_public_key_reuse_and_rotation_without_new_identity_rejected(self):
        config = deepcopy(self.config)
        config["authority_keys"][1]["public_key"] = config["authority_keys"][0]["public_key"]
        with self.assertRaisesRegex(t.TrustError, "duplicate_trust_key"):
            t.SyntheticTrustProvider(canonical(config))
        config = deepcopy(self.config)
        config["authority_keys"][1]["authority_id"] = "authority-A"
        with self.assertRaisesRegex(t.TrustError, "new_authority_identity"):
            t.SyntheticTrustProvider(canonical(config))

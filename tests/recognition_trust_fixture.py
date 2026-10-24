"""Synthetic public-key configuration; private keys exist only in test memory."""

import base64
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import sqlite3
import tempfile
from pathlib import Path
import unittest
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from src.review.recognition import status, trust
from src.review.recognition.rules import canonical
from tests import test_recognition_operations as operation_fixture


NOW = "2026-10-19T12:00:00Z"
ISSUED = "2026-10-19T11:00:00Z"
EXPIRY = "2026-10-22T12:00:00Z"


def offset(seconds, base=NOW):
    return (datetime.strptime(base, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            + timedelta(seconds=seconds)).strftime("%Y-%m-%dT%H:%M:%SZ")


def signed(payload, key, kind="authorization"):
    # Independent implementation: neither production signing-byte helper is used.
    profile = "recognition-authorization-v1" if kind == "authorization" else "recognition-authority-status-v1"
    domain = ("DMV-" + profile).encode("ascii") + bytes([0])
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return json.dumps(dict(format=profile, algorithm="Ed25519", payload=deepcopy(payload),
                           signature=base64.b64encode(key.sign(domain + raw)).decode("ascii")))


class TrustFixture(unittest.TestCase):
    def setUp(self):
        self.fixture = operation_fixture.OperationTests("test_creation_bindings_and_independent_digest")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.operation = self.fixture.make()["envelope"]
        self.operation_json = canonical(self.operation)
        self.keys = {name: Ed25519PrivateKey.generate() for name in ("A", "B", "status")}
        public = lambda name: base64.b64encode(self.keys[name].public_key().public_bytes_raw()).decode("ascii")
        self.config = dict(registry_id="synthetic-registry", authority_keys=[
            dict(authority_id="authority-" + name, key_id="key-" + name, public_key=public(name),
                 grants=[dict(family="first_look", action="finalize"),
                         dict(family="geography_steward", action="finalize")]) for name in ("A", "B")],
            status_keys=[dict(key_id="status-key", public_key=public("status"))])
        self.provider = trust.SyntheticTrustProvider(canonical(self.config))
        self.payload = trust.load(trust.authorization_payload(self.operation_json,
            artifact_id=str(uuid4()), authority_id="authority-A", key_id="key-A", registry_id="synthetic-registry",
            issued_at_utc=ISSUED, expires_at_utc=EXPIRY))
        self.status_payload = dict(registry_id="synthetic-registry", snapshot_id=str(uuid4()), key_id="status-key",
            sequence=1, issued_at_utc=ISSUED, expires_at_utc=EXPIRY,
            authorities=[dict(authority_id="authority-" + name, key_id="key-" + name,
                              state="ENABLED", key_state="ENABLED") for name in ("A", "B")])
        self.temporary = tempfile.TemporaryDirectory(prefix="recognition-status-fixture-")
        self.addCleanup(self.temporary.cleanup)
        self.checkpoint_path = Path(self.temporary.name) / "checkpoint.sqlite"
        self.conn = sqlite3.connect(self.checkpoint_path)
        self.addCleanup(self.conn.close)
        self.conn.execute("BEGIN IMMEDIATE")
        status.install_checkpoint(self.conn)
        self.conn.commit()

    def artifact(self, payload=None, name="A"):
        return signed(self.payload if payload is None else payload, self.keys[name])

    def snapshot(self, payload=None):
        return signed(self.status_payload if payload is None else payload, self.keys["status"], "status")

    def historical(self, artifact=None, **overrides):
        return trust.verify_historical_authorization(self.artifact() if artifact is None else artifact,
            **dict(dict(operation_json=self.operation_json, provider=self.provider), **overrides))

    def current(self, artifact=None, **overrides):
        return trust.verify_current_authorization(self.artifact() if artifact is None else artifact,
            **dict(dict(operation_json=self.operation_json, provider=self.provider,
                        snapshot_json=self.snapshot(), checkpoint_conn=self.conn, trusted_now_utc=NOW), **overrides))

    def check_status(self, snapshot=None, **overrides):
        return status.verify_current_status(self.snapshot() if snapshot is None else snapshot,
            **dict(dict(provider=self.provider, checkpoint_conn=self.conn, trusted_now_utc=NOW), **overrides))

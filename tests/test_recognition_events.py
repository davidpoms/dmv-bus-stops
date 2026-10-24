"""Event foundation tests use only newly created disposable databases."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import importlib
import sqlite3
import unittest
from unittest.mock import patch

from src.review.recognition import events, event_schema
from src.review.recognition.authorization import AuthorizationError, migration_binding
from src.review.recognition.qualification import Quarantined
from src.review.recognition.rules import digest
from src.review.recognition.schema import connection, TABLES as EXPLORER_TABLES
from tests import test_recognition_permanent as fixture
from tests.recognition_authorization_fixture import approval


class EventTests(unittest.TestCase):
    sql = fixture.PermanentFamilyTests.sql
    review = fixture.PermanentFamilyTests.review
    first = fixture.PermanentFamilyTests.first
    geo = fixture.PermanentFamilyTests.geo
    scope = fixture.PermanentFamilyTests.scope
    envelope = fixture.PermanentFamilyTests.envelope

    def setUp(self):
        fixture.PermanentFamilyTests.setUp(self)
        self.review(1)
        self.install()

    def install(self):
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            event_schema.install(conn, **approval(self.path, **migration_binding(
                "recognition_events", event_schema.definitions())))
            conn.commit()

    def request(self, *, geography=False, parent=None):
        manifest = self.geo() if geography else self.first()
        return dict(family=manifest["family"], inputs=manifest["inputs"],
                    evaluation_at_utc=fixture.NOW, review_reference="synthetic-authorization",
                    preparer_id="fixture-preparer", generation_reference="fixture-deployment-v1",
                    parent_event_id=parent)

    def create(self, request=None):
        request = request or self.request()
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            result = events.create_preparation(conn, request, **approval(
                self.path, **events.binding("create_preparation", request)))
            conn.commit()
            return result

    def freeze(self, preparation_id):
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            result = events.freeze_preparation(conn, preparation_id, **approval(
                self.path, **events.binding("freeze_preparation", preparation_id)))
            conn.commit()
            return result

    def state(self, event_id, state, reason="fixture-invalidation"):
        subject = dict(event_id=event_id, state=state, reason=reason)
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            result = events.record_event_state(conn, **subject, **approval(
                self.path, **events.binding("record_event_state", subject)))
            conn.commit()
            return result

    def test_system_population_freeze_and_detached_data(self):
        prepared = self.create()
        self.assertEqual([1], [c["assignment_id"] for c in prepared["manifest"]["candidates"]])
        self.assertEqual([1], [c["physical_stop_id"] for c in prepared["manifest"]["candidates"]])
        frozen = self.freeze(prepared["preparation_id"])
        self.assertEqual("READY", frozen["state"])
        self.assertEqual(prepared, frozen["preparation"])
        self.assertNotEqual(prepared["preparation_id"], frozen["event"]["event_id"])
        self.assertNotEqual(prepared["manifest_sha256"], frozen["event"]["event_id"])
        frozen["preparation"]["manifest"]["candidates"].clear()
        self.assertEqual(1, len(self.freeze(prepared["preparation_id"])["preparation"]["manifest"]["candidates"]))
        bad = self.request()
        bad["candidates"] = []
        with self.assertRaisesRegex(Quarantined, "invalid_preparation_request"):
            self.create(bad)

    def test_geography_preserves_existing_population(self):
        for n in range(2, 6):
            self.review(n)
        prepared = self.create(self.request(geography=True))
        frozen = self.freeze(prepared["preparation_id"])
        candidates = frozen["preparation"]["manifest"]["candidates"]
        self.assertTrue(candidates)
        self.assertEqual({1}, {c["reviewer_id"] for c in candidates})
        self.assertEqual({10}, {c["denominator"] for c in candidates})
        self.assertEqual({5}, {c["numerator"] for c in candidates})

    def test_revision_identity_history_and_duplicate_freeze(self):
        first = self.freeze(self.create()["preparation_id"])
        original = deepcopy(first)
        parent = first["event"]["event_id"]
        request = self.request(parent=parent)
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            prepared = events.create_revision(conn, parent, request, **approval(
                self.path, **events.binding("create_preparation", request)))
            conn.commit()
        revised = self.freeze(prepared["preparation_id"])
        self.assertNotEqual(parent, revised["event"]["event_id"])
        self.assertEqual(parent, revised["event"]["parent_event_id"])
        self.assertEqual(first["preparation"]["manifest_sha256"], prepared["manifest_sha256"])
        self.assertEqual(revised, self.freeze(prepared["preparation_id"]))
        with connection(self.path) as conn:
            self.assertEqual(original, events.get_event(conn, parent))

    def test_stale_preparation_rejected_and_original_retained(self):
        prepared = self.create()
        self.review(2)
        with self.assertRaises(Quarantined):
            self.freeze(prepared["preparation_id"])
        self.assertEqual(1, self.sql("SELECT COUNT(*) FROM recognition_preparations")[0][0])
        self.assertEqual(0, self.sql("SELECT COUNT(*) FROM recognition_frozen_events")[0][0])

    def test_immutable_update_delete_replace_even_without_recursive_triggers(self):
        self.freeze(self.create()["preparation_id"])
        with connection(self.path, write=True) as conn:
            conn.execute("PRAGMA recursive_triggers=OFF")
            for table in event_schema.TABLES:
                for statement in (f"UPDATE {table} SET body_json='{{}}'", f"DELETE FROM {table}",
                                  f"INSERT OR REPLACE INTO {table} SELECT * FROM {table}"):
                    with self.subTest(statement=statement), self.assertRaises(sqlite3.IntegrityError):
                        conn.execute(statement)

    def test_tampered_hash_and_malformed_content_rejected(self):
        frozen = self.freeze(self.create()["preparation_id"])
        event_id = frozen["event"]["event_id"]
        # Simulate privileged corruption, then restore the expected schema.
        trigger = "recognition_frozen_events_immutable_update"
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(f"DROP TRIGGER {trigger}")
            conn.execute("UPDATE recognition_frozen_events SET body_json='{}'")
            conn.execute(event_schema.definitions()[trigger])
            with self.assertRaises(Quarantined):
                events.get_event(conn, event_id)
            conn.execute(f"DROP TRIGGER {trigger}")
            conn.execute("UPDATE recognition_frozen_events SET body_sha256=?", (digest({}),))
            conn.execute(event_schema.definitions()[trigger])
            with self.assertRaisesRegex(Quarantined, "malformed_event"):
                events.get_event(conn, event_id)
            conn.rollback()
        with connection(self.path) as conn:
            self.assertEqual(frozen, events.get_event(conn, event_id))

    def test_states_append_only_and_no_restore(self):
        frozen = self.freeze(self.create()["preparation_id"])
        event_id = frozen["event"]["event_id"]
        stale = self.state(event_id, "STALE")
        self.assertEqual(stale, self.state(event_id, "STALE"))
        invalid = self.state(event_id, "INVALID")
        self.assertEqual(["READY", "STALE", "INVALID"], [h["state"] for h in invalid["history"]])
        self.assertEqual(frozen["event"], invalid["event"])
        for state in ("READY", "STALE", "APPROVED"):
            with self.subTest(state=state), self.assertRaises(Quarantined):
                self.state(event_id, state)

    def test_concurrent_freeze_has_one_identity(self):
        preparation_id = self.create()["preparation_id"]
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(self.freeze, [preparation_id, preparation_id]))
        self.assertEqual(results[0], results[1])
        self.assertEqual(1, self.sql("SELECT COUNT(*) FROM recognition_frozen_events")[0][0])
        self.assertEqual(1, self.sql("SELECT COUNT(*) FROM recognition_event_history")[0][0])

    def test_unauthorized_persistence_and_no_fallback(self):
        request = self.request()
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            with self.assertRaises(AuthorizationError):
                events.create_preparation(conn, request)
            self.assertEqual(0, conn.execute("SELECT COUNT(*) FROM recognition_preparations").fetchone()[0])
        with self.assertRaises(TypeError):
            events.create_preparation(request=request)
        missing = self.path.parent / "never-created.db"
        with self.assertRaises(sqlite3.OperationalError):
            with connection(missing, write=True):
                self.fail("opened missing database")
        self.assertFalse(missing.exists())

    def test_event_data_cannot_authorize_existing_writer(self):
        from src.review.recognition import RecognitionGate, permanent
        from src.review.recognition.authority import provision_production_authority
        frozen = self.freeze(self.create()["preparation_id"])
        manifest = frozen["preparation"]["manifest"]
        with self.assertRaisesRegex(AuthorizationError, "production_authority_not_provisioned"):
            provision_production_authority()
        with self.assertRaises(AuthorizationError):
            permanent.finalize(self.path, manifest, manifest_sha256=digest(manifest),
                               authorization_reference="synthetic-authorization",
                               gate=RecognitionGate(issuance=True), authorization=frozen, authority=frozen)

    def test_preparation_is_immutable_and_new_requests_have_new_identities(self):
        request = self.request()
        prepared = self.create(request)
        original = deepcopy(prepared)
        request["inputs"]["reconciliation"]["expected_assignment_ids"].clear()
        prepared["manifest"]["candidates"].clear()
        frozen = self.freeze(prepared["preparation_id"])
        self.assertEqual(original, frozen["preparation"])
        repeated = self.create()
        self.assertNotEqual(original["preparation_id"], repeated["preparation_id"])
        self.assertEqual(original["manifest_sha256"], repeated["manifest_sha256"])

    def test_explorer_unchanged_and_import_has_no_side_effects(self):
        before = {table: self.sql(f"SELECT * FROM {table}") for table in EXPLORER_TABLES}
        with patch("sqlite3.connect", side_effect=AssertionError("database opened on import")):
            importlib.reload(events)
            importlib.reload(event_schema)
        frozen = self.freeze(self.create()["preparation_id"])
        self.state(frozen["event"]["event_id"], "INVALID")
        self.install()
        self.assertEqual(before, {table: self.sql(f"SELECT * FROM {table}") for table in EXPLORER_TABLES})

    def test_installer_explicit_idempotent_and_rollback_safe(self):
        fresh = self.path.parent / "fresh.db"
        sqlite3.connect(fresh).close()
        approved = approval(fresh, **migration_binding("recognition_events", event_schema.definitions()))
        with connection(fresh, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            with self.assertRaises(AuthorizationError):
                event_schema.install(conn)
            event_schema.install(conn, **approved)
            event_schema.install(conn, **approved)
            conn.rollback()
            self.assertEqual([], conn.execute("SELECT name FROM sqlite_master").fetchall())
            conn.execute("BEGIN IMMEDIATE")
            with patch.object(event_schema, "check_schema", side_effect=Quarantined("injected")):
                with self.assertRaises(Quarantined):
                    event_schema.install(conn, **approved)
            conn.commit()
            self.assertEqual([], conn.execute("SELECT name FROM sqlite_master").fetchall())

    def test_freeze_failure_rolls_back_even_if_caller_commits(self):
        preparation_id = self.create()["preparation_id"]
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            with patch.object(events, "_history", side_effect=Quarantined("injected")):
                with self.assertRaises(Quarantined):
                    events.freeze_preparation(conn, preparation_id, **approval(
                        self.path, **events.binding("freeze_preparation", preparation_id)))
            conn.commit()
        self.assertEqual(0, self.sql("SELECT COUNT(*) FROM recognition_frozen_events")[0][0])


if __name__ == "__main__":
    unittest.main()

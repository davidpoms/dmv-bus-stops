"""Disposable-only permanent family tests; never production artifacts/bindings."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import hashlib
import sqlite3
import unittest
from unittest.mock import patch

from src.review.recognition import RecognitionGate
from src.review.recognition import permanent
from src.review.recognition.geography import build_geography_report
from src.review.recognition.permanent_schema import TABLES, check_schema, install, migrate
from src.review.recognition.qualification import Quarantined
from src.review.recognition.rules import canonical, digest
from src.review.recognition.schema import connection, migrate as explorer_migrate
from tests import test_recognition_geography as geography_fixture


ISSUE = RecognitionGate(issuance=True)
NOW = "2026-10-01T00:00:00Z"


class PermanentFamilyTests(unittest.TestCase):
    sql = geography_fixture.GeographyReportTests.sql
    review = geography_fixture.GeographyReportTests.review
    scope = geography_fixture.GeographyReportTests.scope
    envelope = geography_fixture.GeographyReportTests.envelope

    def setUp(self):
        geography_fixture.GeographyReportTests.setUp(self)
        explorer_migrate(self.path, apply=True)

    def first(self):
        inputs = {"cutoff_utc": NOW, "reconciliation": {
            "reference": "synthetic-cohort-review", "clock_review_reference": "synthetic-clock-review",
            "identity_review_reference": "synthetic-identity-review",
            "expected_assignment_ids": [r[0] for r in self.sql("SELECT id FROM stop_review_assignments ORDER BY id")]}}
        return permanent.prepare(self.path, family="first_look", inputs=inputs,
                                 evaluation_at_utc=NOW, authorization_reference="synthetic-authorization")

    def geo(self, scope=None):
        scope = deepcopy(scope or self.scope())
        scope.update(display_label="ANC 1D", quality_findings=[], identity_review_reference="synthetic-identity-review")
        scope["certification"]["independent"] = True
        inputs = {"scope_snapshot": self.envelope([scope]), "cutoff_utc": NOW}
        report = build_geography_report(self.path, **inputs)
        inputs["reconciliation"] = {"reference": "synthetic-cohort-review", "source_sha256": report["source_sha256"]}
        return permanent.prepare(self.path, family="geography_steward", inputs=inputs,
                                 evaluation_at_utc=NOW, authorization_reference="synthetic-authorization")

    def seal(self, manifest):
        return permanent.finalize(self.path, manifest, manifest_sha256=digest(manifest),
                                  authorization_reference="synthetic-authorization", gate=ISSUE)

    def counts(self):
        return {table: self.sql(f"SELECT COUNT(*) FROM {table}")[0][0] for table in TABLES}

    def test_default_off_never_opens_database(self):
        with patch.object(permanent, "connection", side_effect=AssertionError("opened")):
            self.assertFalse(permanent.finalize("missing", {}, manifest_sha256="")["issued"])

    def test_migration_dry_run_repeat_and_explorer_unchanged(self):
        self.review(1)
        before = self.path.read_bytes()
        self.assertFalse(migrate(self.path)["applied"])
        self.assertEqual(before, self.path.read_bytes())
        old = self.sql("SELECT * FROM recognition_completions"), self.sql("SELECT * FROM recognition_jobs")
        migrate(self.path, apply=True)
        migrate(self.path, apply=True)
        self.assertEqual(old, (self.sql("SELECT * FROM recognition_completions"), self.sql("SELECT * FROM recognition_jobs")))
        self.assertTrue(all(n == 0 for n in self.counts().values()))

    def test_migration_rollback_and_incompatible_schema(self):
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            install(conn)
        self.assertFalse(self.sql("SELECT name FROM sqlite_master WHERE name='recognition_private_rules'"))
        self.sql("CREATE TABLE recognition_private_rules(bad TEXT)")
        with self.assertRaises(Quarantined):
            migrate(self.path, apply=True)
        self.assertFalse(self.sql("SELECT name FROM sqlite_master WHERE name='recognition_first_look_claims'"))

    def test_first_look_competitors_numeric_tie_and_read_only_preparation(self):
        self.review(10, stop=1, owner=1)
        self.review(2, stop=1, owner=2)
        before = hashlib.sha256(self.path.read_bytes()).hexdigest()
        manifest = self.first()
        self.assertEqual(before, hashlib.sha256(self.path.read_bytes()).hexdigest())
        self.assertEqual([(2, 2)], [(c["assignment_id"], c["reviewer_id"]) for c in manifest["candidates"]])
        migrate(self.path, apply=True)
        self.seal(manifest)
        with connection(self.path) as conn:
            self.assertEqual(2, permanent.check_claim_integrity(conn, 1)["reviewer_id"])
        self.assertEqual(0, self.sql("SELECT COUNT(*) FROM recognition_awards")[0][0])
        self.assertEqual(2, self.sql("SELECT COUNT(*) FROM recognition_jobs WHERE state='pending' AND attempts=0")[0][0])

    def test_missing_capture_and_unattributed_identity_event_block(self):
        self.review(1, captured=False)
        with self.assertRaisesRegex(Quarantined, "competitor_completion_not_captured"):
            self.first()
        self.sql("INSERT INTO physical_stop_identity_events VALUES(1,'move')")
        with self.assertRaisesRegex(Quarantined, "unattributed_identity_event"):
            self.first()

    def test_identity_affected_stop_is_withheld(self):
        self.review(1)
        self.review(3)
        self.sql("INSERT INTO physical_stop_identity_events VALUES(1,'merge')")
        self.sql("INSERT INTO physical_stop_identity_edges VALUES(1,1,2)")
        manifest = self.first()
        self.assertEqual([3], [c["physical_stop_id"] for c in manifest["candidates"]])

    def test_timestamp_and_missing_competitor_are_not_silently_sealed(self):
        self.review(1)
        self.review(2, stop=1, timestamp="2026-09-24 12:00:00", captured=False)
        self.assertEqual([], self.first()["candidates"])
        self.sql("INSERT INTO stop_observations VALUES(10,999,2,1,'community_review')")
        with self.assertRaisesRegex(Quarantined, "historical_population_unreviewed"):
            self.first()

    def test_first_look_concurrent_sealing_is_idempotent(self):
        self.review(1)
        migrate(self.path, apply=True)
        manifest = self.first()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(self.seal, [manifest, manifest]))
        self.assertEqual(1, sum(r["issued"] for r in results))
        self.assertEqual(1, self.counts()["recognition_first_look_claims"])

    def test_source_race_rolls_back_before_write(self):
        self.review(1)
        migrate(self.path, apply=True)
        manifest = self.first()
        self.sql("UPDATE stop_review_assignments SET completed_at='2026-09-24T12:00:00Z' WHERE id=1")
        with self.assertRaises(Quarantined):
            self.seal(manifest)
        self.assertTrue(all(n == 0 for n in self.counts().values()))

    def test_writer_lock_and_atomic_failure(self):
        self.review(1)
        self.review(2)
        migrate(self.path, apply=True)
        manifest = self.first()
        original = permanent._prepare
        def locked(conn, *args):
            self.assertTrue(conn.in_transaction)
            with connection(self.path, write=True) as other:
                other.execute("PRAGMA busy_timeout=1")
                with self.assertRaises(sqlite3.OperationalError):
                    other.execute("BEGIN IMMEDIATE")
            return original(conn, *args)
        with patch.object(permanent, "_prepare", side_effect=locked), patch.object(
                permanent, "check_claim_integrity", side_effect=Quarantined("synthetic-failure-after-inserts")):
            with self.assertRaises(Quarantined):
                self.seal(manifest)
        self.assertTrue(all(n == 0 for n in self.counts().values()))
        self.assertTrue(self.seal(manifest)["issued"])

    def test_late_discrepancy_does_not_reassign_claim(self):
        self.review(1)
        migrate(self.path, apply=True)
        manifest = self.first()
        self.seal(manifest)
        self.review(2, stop=1, owner=2, timestamp="2026-09-24T12:00:00Z")
        with self.assertRaisesRegex(Quarantined, "existing_claim_requires_discrepancy"):
            self.seal(self.first())
        kwargs = dict(physical_stop_id=1, evidence={"reason": "late_earlier_completion", "assignment_id": 2},
                      review_reference="synthetic-discrepancy-review", reviewed_at_utc=NOW, gate=ISSUE)
        self.assertEqual(permanent.append_discrepancy(self.path, **kwargs), permanent.append_discrepancy(self.path, **kwargs))
        self.assertEqual([(1, 1)], self.sql("SELECT physical_stop_id,reviewer_id FROM recognition_first_look_claims"))
        self.assertEqual(1, self.counts()["recognition_first_look_discrepancies"])
        self.assertTrue(self.seal(manifest)["idempotent"])

    def test_wrong_hash_authorization_and_capture_gate(self):
        self.review(1)
        migrate(self.path, apply=True)
        manifest = self.first()
        for changes in ({"manifest_sha256": "0" * 64}, {"authorization_reference": None},
                        {"gate": RecognitionGate(capture=True, issuance=True)}):
            kwargs = dict(manifest_sha256=digest(manifest), authorization_reference="synthetic-authorization", gate=ISSUE)
            kwargs.update(changes)
            with self.assertRaises(Quarantined):
                permanent.finalize(self.path, manifest, **kwargs)
        self.assertTrue(all(n == 0 for n in self.counts().values()))

    def test_immutable_update_delete_replace(self):
        self.review(1)
        migrate(self.path, apply=True)
        self.seal(self.first())
        for query in ("DELETE FROM recognition_first_look_claims", "UPDATE recognition_first_look_claims SET reviewer_id=2",
                      "INSERT OR REPLACE INTO recognition_first_look_claims SELECT * FROM recognition_first_look_claims"):
            with self.assertRaises(sqlite3.IntegrityError):
                self.sql(query)

    def test_tampered_schema_rejected_before_issuance(self):
        self.review(1)
        migrate(self.path, apply=True)
        manifest = self.first()
        self.sql("DROP TRIGGER recognition_first_look_claims_immutable_update")
        with self.assertRaisesRegex(Quarantined, "private_schema_mismatch"):
            self.seal(manifest)
        self.assertTrue(all(n == 0 for n in self.counts().values()))

    def test_geography_catch_up_tiers_witnesses_and_frozen_denominator(self):
        for n in range(1, 6):
            self.review(n)
        migrate(self.path, apply=True)
        manifest = self.geo()
        self.assertEqual(["tier_1", "tier_2"], sorted(c["tier_key"] for c in manifest["candidates"]))
        self.seal(manifest)
        self.assertTrue(self.seal(manifest)["idempotent"])
        self.sql("UPDATE stop_gtfs_status SET current_gtfs=0")
        with connection(self.path) as conn:
            for candidate in manifest["candidates"]:
                fact = permanent.check_geography_integrity(conn, digest(candidate))
                self.assertEqual((5, 10, NOW), (fact["numerator"], fact["denominator"], fact["earned_at_utc"]))
        self.assertEqual(10, self.counts()["recognition_geography_witnesses"])
        self.assertEqual(0, self.sql("SELECT COUNT(*) FROM recognition_awards")[0][0])

    def test_geography_membership_race_and_denominator_shrink_protection(self):
        for n in range(1, 6):
            self.review(n)
        migrate(self.path, apply=True)
        manifest = self.geo(self.scope(20))
        self.sql("UPDATE stop_gtfs_status SET current_gtfs=0 WHERE physical_stop_id=10")
        with self.assertRaisesRegex(Quarantined, "current_active_membership_changed"):
            self.seal(manifest)
        self.sql("UPDATE stop_gtfs_status SET current_gtfs=1 WHERE physical_stop_id=10")
        self.seal(manifest)
        with self.assertRaisesRegex(Quarantined, "scope_catch_up_already_sealed"):
            self.seal(self.geo(self.scope(10)))

    def test_uncertified_and_duplicate_members_rejected(self):
        self.review(1)
        scope = self.scope()
        scope["certification"]["approved"] = False
        with self.assertRaises(Quarantined):
            self.geo(scope)
        scope = self.scope()
        scope["members"].append(dict(scope["members"][0]))
        scope["membership_sha256"] = digest(scope["members"])
        with self.assertRaisesRegex(Quarantined, "exact_active_members_required"):
            self.geo(scope)

    def test_stable_ordinal_tiers_across_size_bands(self):
        for n in range(1, 11):
            self.review(n)
        small = self.geo(self.scope(20))["candidates"]
        large = self.geo(self.scope(100))["candidates"]
        self.assertEqual([("tier_1", 25), ("tier_2", 50)], sorted((c["tier_key"], c["percentage"]) for c in small))
        self.assertEqual([("tier_1", 10)], [(c["tier_key"], c["percentage"]) for c in large])

    def test_complete_competitor_population_and_observation_races(self):
        self.review(1)
        migrate(self.path, apply=True)
        manifest = self.first()
        self.review(2, stop=1, owner=2, timestamp="2026-09-24T12:00:00Z")
        with self.assertRaises(Quarantined):
            self.seal(manifest)
        manifest = self.first()
        self.sql("UPDATE stop_observations SET reviewer_id=1 WHERE id=2")
        with self.assertRaises(Quarantined):
            self.seal(manifest)
        self.assertTrue(all(n == 0 for n in self.counts().values()))

    def test_inactive_historical_first_look_does_not_require_current_gtfs(self):
        self.review(1)
        self.sql("UPDATE stop_gtfs_status SET current_gtfs=0 WHERE physical_stop_id=1")
        migrate(self.path, apply=True)
        self.assertEqual(1, self.seal(self.first())["records"])

    def test_frozen_geography_witness_tampering_is_detected(self):
        for n in range(1, 6):
            self.review(n)
        migrate(self.path, apply=True)
        manifest = self.geo()
        self.seal(manifest)
        # Simulate external corruption in this disposable fixture only.
        self.sql("DROP TRIGGER recognition_geography_witnesses_immutable_delete")
        self.sql("DELETE FROM recognition_geography_witnesses WHERE assignment_id=1")
        with connection(self.path) as conn:
            with self.assertRaisesRegex(Quarantined, "geography_witness_set_mismatch"):
                permanent.check_geography_integrity(conn, digest(manifest["candidates"][0]))

    def test_unexpected_writer_trigger_and_report_transaction_control_rejected(self):
        self.review(1)
        migrate(self.path, apply=True)
        manifest = self.first()
        self.sql("CREATE TRIGGER synthetic_bad AFTER INSERT ON recognition_first_look_claims BEGIN UPDATE community_reviewers SET id=id; END")
        with self.assertRaisesRegex(Quarantined, "unexpected_private_trigger"):
            self.seal(manifest)
        from src.review.recognition.report_connection import report_connection
        with connection(self.path, write=True) as conn:
            conn.execute("BEGIN IMMEDIATE")
            with report_connection(conn):
                for sql in ("COMMIT", "DELETE FROM recognition_completions", "PRAGMA query_only=OFF"):
                    with self.assertRaises(sqlite3.DatabaseError):
                        conn.execute(sql)
            self.assertTrue(conn.in_transaction)

    def test_geography_later_witness_failure_rolls_back_all_tiers(self):
        for n in range(1, 6):
            self.review(n)
        migrate(self.path, apply=True)
        manifest = self.geo()
        original = permanent.check_geography_integrity
        calls = []
        def fail_second(conn, award):
            calls.append(award)
            if len(calls) == 2:
                raise Quarantined("synthetic-later-witness-failure")
            return original(conn, award)
        with patch.object(permanent, "check_geography_integrity", side_effect=fail_second):
            with self.assertRaises(Quarantined):
                self.seal(manifest)
        self.assertEqual(2, len(calls))
        self.assertTrue(all(n == 0 for n in self.counts().values()))
        self.assertTrue(self.seal(manifest)["issued"])


class PermanentAchievementsTests(unittest.TestCase):
    sql = PermanentFamilyTests.sql
    review = PermanentFamilyTests.review
    scope = PermanentFamilyTests.scope
    envelope = PermanentFamilyTests.envelope
    first = PermanentFamilyTests.first
    geo = PermanentFamilyTests.geo
    seal = PermanentFamilyTests.seal

    def setUp(self):
        PermanentFamilyTests.setUp(self)
        self.sql("ALTER TABLE community_reviewers ADD COLUMN reviewer_key TEXT")
        self.sql("UPDATE community_reviewers SET reviewer_key='owner-key' WHERE id=1")
        self.sql("UPDATE community_reviewers SET reviewer_key='other-key' WHERE id=2")
        for n in range(1, 6):
            self.review(n)
        self.review(20, owner=2)
        migrate(self.path, apply=True)
        self.seal(self.first())
        self.seal(self.geo())
        from src.api import app as api
        self.api = api
        config = {key: api.app.config[key] for key in ("TESTING", "SECRET_KEY")}
        self.addCleanup(api.app.config.update, config)
        api.app.config.update(TESTING=True, SECRET_KEY="synthetic-private-families")
        database_patch = patch.object(api, "DATABASE_PATH", self.path)
        database_patch.start()
        self.addCleanup(database_patch.stop)
        self.client = api.app.test_client()
        self.login()

    def login(self, owner=1, key="owner-key"):
        with self.client.session_transaction() as session:
            session.clear()
            session["authenticated_reviewer_id"] = owner
            session["reviewer_key"] = key

    def test_private_owner_display_contract_and_read_only(self):
        before = self.path.read_bytes()
        response = self.client.get("/api/reviewer/achievements")
        self.assertEqual(200, response.status_code)
        self.assertEqual("private, no-store", response.headers["Cache-Control"])
        rows = response.get_json()["achievements"]
        self.assertEqual(5, sum(r["family"] == "first_look" for r in rows))
        self.assertEqual(2, sum(r["family"] == "geography_steward" for r in rows))
        for row in rows:
            self.assertTrue(set(row).isdisjoint({"reviewer_id", "physical_stop_id", "assignment_id", "witnesses", "evidence_json", "reviewer_key", "rule_key"}))
        self.assertEqual(before, self.path.read_bytes())
        self.login(2, "other-key")
        other = self.client.get("/api/reviewer/achievements").get_json()["achievements"]
        self.assertEqual(1, len(other))
        self.assertEqual("claim", other[0]["recognition_kind"])

    def test_integrity_failure_does_not_expose_partial_results(self):
        from src.review.recognition import achievements
        for name in ("check_claim_integrity", "check_geography_integrity"):
            with patch.object(achievements, name, side_effect=Quarantined("synthetic-corruption")):
                response = self.client.get("/api/reviewer/achievements")
                self.assertEqual(503, response.status_code)
                self.assertNotIn("achievements", response.get_json())

    def test_authentication_and_request_contract_unchanged(self):
        self.assertEqual(400, self.client.get("/api/reviewer/achievements?owner=2").status_code)
        self.assertEqual(400, self.client.get("/api/reviewer/achievements", data=b"{}").status_code)
        self.login(1, "other-key")
        self.assertEqual(403, self.client.get("/api/reviewer/achievements").status_code)
        with self.client.session_transaction() as session:
            session.clear()
        response = self.client.get("/api/reviewer/achievements")
        self.assertEqual(401, response.status_code)
        self.assertEqual("private, no-store", response.headers["Cache-Control"])


if __name__ == "__main__":
    unittest.main()

import inspect
import importlib
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.assessment.amenity_recommendation_policy import (
    LOCAL_SOURCE_PUBLIC_LABELS,
)
from src.assessment.generate_bench_installation_candidates import (
    build_candidate,
    classify_clearance,
    classify_next_action,
    generate_candidates,
    ranking_key,
)


class BenchCandidatePolicyTests(unittest.TestCase):
    def candidate(self, status="likely_no", negative=None, score=80,
                  conflict=0, yes=0, no=0):
        return build_candidate(
            physical_stop_id=1, primary_name="Example", state="VA",
            county="Alexandria", municipality="Alexandria",
            canonical_status=status, consensus_status="not_reached",
            community_negative_count=1 if negative and negative.get("community_negative") else 0,
            evidence_conflict=conflict, consensus_conflict=0,
            opportunity_score=score, rider_exposure_percentile=90,
            review_priority_score=70, review_priority_tier="high",
            clearance_yes_count=yes, clearance_no_count=no,
            negative_evidence=negative or {},
        )

    def test_confirmed_local_and_corroborated_absence_are_eligible(self):
        confirmed = self.candidate("confirmed_no")
        self.assertEqual("high", confirmed["recommendation_confidence"])
        local = self.candidate(negative={"high_local_sources": {"ALEXANDRIA"}})
        self.assertEqual("medium", local["recommendation_confidence"])
        corroborated = self.candidate(negative={
            "medium_local_sources": {"ALEXANDRIA"}, "osm_negative": True,
        })
        self.assertEqual("corroborated_likely_absence", corroborated["evidence_strength"])

    def test_weak_or_contradictory_statuses_are_excluded(self):
        for status in ("likely_yes", "confirmed_yes", "conflicting", "unknown"):
            self.assertIsNone(self.candidate(status, {"high_local_sources": {"ALEXANDRIA"}}))
        for negative in (
            {"osm_negative": True}, {"community_negative": True},
            {"low_local_sources": {"ALEXANDRIA"}},
            {"high_local_sources": {"DDOT"}},
            {"high_local_sources": {"UNKNOWN"}},
        ):
            self.assertIsNone(self.candidate(negative=negative))
        self.assertIsNone(self.candidate(
            negative={"high_local_sources": {"ALEXANDRIA"}}, conflict=1
        ))

    def test_clearance_is_preliminary_and_candidate_may_be_unknown(self):
        self.assertEqual("unknown", classify_clearance(0, 0))
        self.assertEqual("observed_clear", classify_clearance(1, 0))
        self.assertEqual("observed_constrained", classify_clearance(1, 1))
        candidate = self.candidate(
            negative={"high_local_sources": {"ALEXANDRIA"}}
        )
        self.assertEqual("unknown", candidate["clearance_status"])
        self.assertEqual("collect_clearance_observation", candidate["next_action"])
        self.assertNotIn("engineering feasibility", " ".join(candidate["rationale"]).lower())

    def test_next_actions_are_deterministic(self):
        self.assertEqual("candidate_ready_for_planning", classify_next_action("confirmed_no", "observed_clear"))
        self.assertEqual("collect_clearance_observation", classify_next_action("likely_no", "unknown"))
        self.assertEqual("planning_review", classify_next_action("likely_no", "observed_clear"))
        self.assertEqual("planning_review", classify_next_action("confirmed_no", "observed_constrained"))

    def test_ranking_uses_exposure_only_after_readiness_evidence_and_score(self):
        source = inspect.getsource(ranking_key)
        self.assertNotIn("route_exposure", source)
        self.assertLess(source.index("opportunity_score"), source.index("rider_exposure_percentile"))

    def test_public_source_copy_is_local_not_wmata_authority(self):
        self.assertEqual(
            "Montgomery County inventory",
            LOCAL_SOURCE_PUBLIC_LABELS["MONTGOMERY_COUNTY_WMATA"],
        )
        from src.assessment import generate_bench_installation_candidates
        source = inspect.getsource(generate_bench_installation_candidates)
        self.assertNotIn("wmata_bench", source)
        self.assertNotIn("wmata_shelter", source)
        self.assertNotIn("source='DDOT'", source)


class BenchCandidateRebuildTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "bench.db"
        c = sqlite3.connect(self.path)
        c.executescript("""
            CREATE TABLE stop_gtfs_status(physical_stop_id INTEGER,current_gtfs INTEGER);
            CREATE TABLE physical_stops(id INTEGER PRIMARY KEY,primary_name TEXT);
            CREATE TABLE stop_jurisdiction(stop_id INTEGER,state TEXT,county TEXT,municipality TEXT);
            CREATE TABLE stop_amenity_status(physical_stop_id INTEGER,amenity_type TEXT,derived_status TEXT,consensus_status TEXT,local_yes_count INTEGER,osm_yes INTEGER,community_yes_count INTEGER,community_no_count INTEGER,osm_no INTEGER,evidence_conflict INTEGER,consensus_conflicts_with_other_evidence INTEGER);
            CREATE TABLE improvement_opportunities(physical_stop_id INTEGER,opportunity_score REAL);
            CREATE TABLE opportunity_assessments(physical_stop_id INTEGER,rider_exposure_percentile REAL);
            CREATE TABLE stop_amenity_review_priority(physical_stop_id INTEGER,amenity_type TEXT,review_priority_score REAL,priority_tier TEXT);
            CREATE TABLE stop_observations(id INTEGER,physical_stop_id INTEGER,source TEXT,bench_feasible TEXT);
            CREATE TABLE stop_amenity_evidence(physical_stop_id INTEGER,amenity_type TEXT,present INTEGER,source TEXT,confidence TEXT);
            INSERT INTO physical_stops VALUES(1,'Active'),(2,'Inactive'),(3,'OSM only');
            INSERT INTO stop_gtfs_status VALUES(1,1),(2,0),(3,1);
            INSERT INTO stop_jurisdiction VALUES(1,'VA','Alexandria','Alexandria'),(2,'VA','Alexandria','Alexandria'),(3,'DC',NULL,NULL);
            INSERT INTO stop_amenity_status VALUES(1,'bench','likely_no','not_reached',0,0,0,0,0,0,0),(2,'bench','likely_no','not_reached',0,0,0,0,0,0,0),(3,'bench','likely_no','not_reached',0,0,0,0,1,0,0);
            INSERT INTO improvement_opportunities VALUES(1,80),(2,90),(3,95);
            INSERT INTO opportunity_assessments VALUES(1,50),(2,99),(3,100);
            INSERT INTO stop_amenity_review_priority VALUES(1,'bench',60,'medium'),(2,'bench',80,'high'),(3,'bench',90,'high');
            INSERT INTO stop_observations VALUES(1,1,'community_review','yes');
            INSERT INTO stop_amenity_evidence VALUES(1,'bench',0,'ALEXANDRIA','high'),(2,'bench',0,'ALEXANDRIA','high');
        """)
        c.commit()
        c.close()

    def tearDown(self):
        self.tmp.cleanup()

    def test_rebuild_enforces_active_scope_preserves_observations_and_excludes_osm_only(self):
        generate_candidates(self.path)
        c = sqlite3.connect(self.path)
        self.assertEqual([(1,)], c.execute("SELECT physical_stop_id FROM bench_installation_candidates").fetchall())
        self.assertEqual(1, c.execute("SELECT COUNT(*) FROM stop_observations").fetchone()[0])
        row = c.execute("SELECT clearance_status,next_action FROM bench_installation_candidates").fetchone()
        self.assertEqual(("observed_clear", "planning_review"), row)
        c.close()

    def test_api_exposes_summary_and_filters_without_raw_authority_metadata(self):
        generate_candidates(self.path)
        api_app = importlib.import_module("src.api.app")
        with patch.object(api_app, "DATABASE_PATH", self.path):
            client = api_app.app.test_client()
            payload = client.get("/bench-candidates").get_json()
            self.assertEqual(1, payload["summary"]["bench_candidates"])
            candidate = payload["candidates"][0]
            self.assertEqual("City of Alexandria inventory", candidate["local_negative_sources"][0])
            self.assertFalse(candidate["engineering_feasibility_established"])
            self.assertNotIn("source_metadata", candidate)
            filtered = client.get("/bench-candidates?state=DC").get_json()
            self.assertEqual([], filtered["candidates"])


if __name__ == "__main__":
    unittest.main()

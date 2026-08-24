import inspect
import unittest

from src.api.app import stop_review_summary
from src.assessment.generate_improvement_recommendations import (
    build_amenity_recommendations,
    source_applies_to_jurisdiction,
)
from src.assessment.interpretation import (
    amenity_status_sentence,
    interpret_bench_status,
)
from src.assessment.score_improvement_opportunities import (
    calculate_amenity_gap,
)
from src.assessment import generate_improvement_recommendations
from src.assessment import score_improvement_opportunities


class CanonicalAmenityRecommendationTests(unittest.TestCase):
    def recommendations(
        self, amenity, status, observations=0, negative=None,
        clearance_yes=3, clearance_no=0,
    ):
        return build_amenity_recommendations(
            amenity, status, 80, observations, negative,
            clearance_yes if amenity == "bench" else 0,
            clearance_no if amenity == "bench" else 0,
        )

    def test_confirmed_statuses_are_resolved(self):
        for amenity in ("bench", "shelter"):
            with self.subTest(amenity=amenity, status="confirmed_yes"):
                self.assertEqual([], self.recommendations(amenity, "confirmed_yes", 3))
            with self.subTest(amenity=amenity, status="confirmed_no"):
                rows = self.recommendations(amenity, "confirmed_no", 3)
                if amenity == "bench":
                    self.assertFalse(any("installation" in row["type"] for row in rows))
                else:
                    self.assertEqual(f"{amenity}_installation_candidate", rows[0]["type"])
                    self.assertEqual("high", rows[0]["confidence"])

    def test_likely_statuses_preserve_uncertainty(self):
        for amenity in ("bench", "shelter"):
            with self.subTest(amenity=amenity, status="likely_yes"):
                rows = self.recommendations(amenity, "likely_yes", 1)
                self.assertEqual(f"{amenity}_presence_review", rows[0]["type"])
                self.assertNotIn("installation", rows[0]["type"])
            with self.subTest(amenity=amenity, status="likely_no"):
                rows = self.recommendations(
                    amenity, "likely_no", 1,
                    {"high_local_sources": {"ALEXANDRIA"}},
                )
                if amenity == "bench":
                    self.assertFalse(any("installation" in row["type"] for row in rows))
                else:
                    self.assertEqual(f"{amenity}_installation_candidate", rows[0]["type"])
                    self.assertEqual("medium", rows[0]["confidence"])
                    self.assertTrue(any("consensus has not been reached" in reason
                                        for reason in rows[0]["reasons"]))

    def test_likely_no_requires_eligible_provenance(self):
        for amenity in ("bench", "shelter"):
            for negative in (
                {"osm_negative": True},
                {"community_negative": True},
                {"high_local_sources": {"UNKNOWN_FUTURE_SOURCE"}},
                {"high_local_sources": {"DDOT_ARCGIS"}},
                {"high_local_sources": {"FAIRFAX_COUNTY"}},
                {"high_local_sources": {"FALLS_CHURCH_CITY"}},
                {"high_local_sources": {"DDOT"}},
                {"low_local_sources": {"ALEXANDRIA"}},
            ):
                with self.subTest(amenity=amenity, negative=negative):
                    rows = self.recommendations(
                        amenity, "likely_no", negative=negative
                    )
                    self.assertFalse(any("installation" in row["type"] for row in rows))

    def test_corroboration_and_match_quality(self):
        for amenity in ("bench", "shelter"):
            medium_only = self.recommendations(
                amenity, "likely_no",
                negative={"medium_local_sources": {"ALEXANDRIA"}},
            )
            self.assertFalse(any("installation" in row["type"] for row in medium_only))
            corroborated = self.recommendations(
                amenity, "likely_no",
                negative={
                    "medium_local_sources": {"ALEXANDRIA"},
                    "osm_negative": True,
                },
            )
            if amenity == "bench":
                self.assertFalse(any("installation" in row["type"] for row in corroborated))
            else:
                self.assertEqual(
                    f"{amenity}_installation_candidate", corroborated[0]["type"]
                )
                self.assertIn("Multiple independent", corroborated[0]["reasons"][0])

    def test_osm_requires_explicit_identity_matched_canonical_signal(self):
        for negative in ({}, {"osm_proximity_only": True}, {"osm_missing": True}):
            rows = self.recommendations("shelter", "likely_no", negative=negative)
            self.assertFalse(any("installation" in row["type"] for row in rows))

    def test_local_sources_are_authoritative_only_in_their_jurisdiction(self):
        self.assertTrue(source_applies_to_jurisdiction(
            "MONTGOMERY_COUNTY_WMATA", "MD", "Montgomery"
        ))
        self.assertFalse(source_applies_to_jurisdiction(
            "MONTGOMERY_COUNTY_WMATA", "DC", "Montgomery"
        ))
        self.assertFalse(source_applies_to_jurisdiction(
            "ALEXANDRIA", "VA", "Arlington"
        ))
        self.assertFalse(source_applies_to_jurisdiction(
            "UNKNOWN_FUTURE_SOURCE", "MD", "Montgomery"
        ))

    def test_bench_clearance_is_preliminary_and_not_feasibility_review(self):
        negative = {"high_local_sources": {"ALEXANDRIA"}}
        one = self.recommendations(
            "bench", "likely_no", observations=1, negative=negative,
            clearance_yes=1,
        )
        self.assertFalse(any("installation" in row["type"] for row in one))
        self.assertFalse(any(row["type"] == "bench_feasibility_review" for row in one))
        three = self.recommendations(
            "bench", "likely_no", observations=3, negative=negative,
            clearance_yes=3,
        )
        self.assertFalse(any("installation" in row["type"] for row in three))

    def test_conflicting_and_unknown_are_verification_not_installation(self):
        for amenity in ("bench", "shelter"):
            with self.subTest(amenity=amenity, status="conflicting"):
                rows = self.recommendations(amenity, "conflicting")
                self.assertEqual(f"{amenity}_presence_review", rows[0]["type"])
                self.assertEqual("high", rows[0]["confidence"])
            with self.subTest(amenity=amenity, status="unknown"):
                rows = self.recommendations(amenity, "unknown", 1)
                self.assertEqual(f"{amenity}_presence_review", rows[0]["type"])
                self.assertEqual([], self.recommendations(amenity, "unknown", 0))

    def test_score_uses_absence_only_and_does_not_add_rider_percentile(self):
        self.assertEqual(100, calculate_amenity_gap("confirmed_no", "likely_no"))
        self.assertEqual(0, calculate_amenity_gap("unknown", "conflicting"))
        source = inspect.getsource(score_improvement_opportunities)
        self.assertIn("route_exposure_score", source)
        self.assertNotIn("rider_exposure_percentile", source)

    def test_raw_sources_cannot_bypass_canonical_status(self):
        evidence = {
            "amenity_status": {"bench": {"derived_status": "confirmed_yes"}},
            "osm": {"osm_bench": 0},
            "wmata": {"wmata_bench": 0},
            "ddot": [{"lifecycle_status": "CONFIRMED_ACTIVE"}],
        }
        self.assertEqual("confirmed_yes", interpret_bench_status(evidence)["status"])
        evidence["amenity_status"]["bench"]["derived_status"] = "unknown"
        evidence["osm"]["osm_bench"] = 1
        self.assertEqual("unknown", interpret_bench_status(evidence)["status"])
        source = inspect.getsource(generate_improvement_recommendations)
        for stale_name in ("stop_osm_evidence", "wmata_bench", "wmata_shelter", "source = 'DDOT'"):
            self.assertNotIn(stale_name, source)

    def test_public_wording_and_api_use_canonical_status(self):
        self.assertIn("insufficient", amenity_status_sentence("shelter", "unknown"))
        self.assertIn("conflicts", amenity_status_sentence("bench", "conflicting"))
        source = inspect.getsource(stop_review_summary)
        self.assertIn("amenity_status", source)
        self.assertNotIn("osm_bench", source)
        self.assertNotIn("osm_shelter", source)


if __name__ == "__main__":
    unittest.main()

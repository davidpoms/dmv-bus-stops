import unittest
from pathlib import Path

from src.review.context import build_review_context, evidence_explanation


ROOT = Path(__file__).resolve().parents[1]


class ReviewContextUxTests(unittest.TestCase):
    def opportunity(self, **changes):
        value = {
            "bench_status": "unknown",
            "adequacy_status": "unknown",
            "clearance_status": "unknown",
            "workflow_state": "verify_presence",
            "strongest_need_signal": "no_documented_need",
        }
        value.update(changes)
        return value

    def test_entry_explanations_are_pathway_accurate_and_need_is_shared(self):
        opportunity = self.opportunity(bench_status="likely_no")
        expected = {
            "opportunity": "reviewing a seating opportunity selected",
            "route": "route you chose to review",
            "nearby": "near the area you chose to review",
            "map": "You chose this stop",
            "direct": "You chose this stop",
        }
        needs = set()
        for scenario, phrase in expected.items():
            context = build_review_context(scenario, opportunity)
            self.assertIn(phrase, context["entry_explanation"])
            needs.add(context["evidence_explanation"])
        self.assertEqual(1, len(needs))
        self.assertNotIn("Opportunity Review", build_review_context(
            "route", opportunity
        )["entry_explanation"])
        self.assertNotIn("selected", build_review_context(
            "direct", opportunity
        )["entry_explanation"])

    def test_evidence_explanations_are_cautious_and_plain_language(self):
        cases = (
            ({"bench_status": "likely_no"}, "suggest", "confirmed"),
            ({"bench_status": "confirmed_no"}, "may not have a bench", None),
            ({"bench_status": "likely_yes"}, "appears to be present", "confirmed"),
            ({"bench_status": "confirmed_yes"}, "recorded as present", None),
            ({"adequacy_status": "limitation_observed"}, "limited or uncomfortable", None),
            ({"strongest_need_signal": "poor_comfort_evidence"}, "limited or uncomfortable", None),
            ({"bench_status": "conflicting"}, "sources disagree", None),
            ({"bench_status": "unknown"}, "not yet have enough reliable information", None),
            ({"workflow_state": "collect_clearance_observation"}, "preliminary visual check", None),
            ({"clearance_status": "observed_constrained"}, "limited pass-through space", "infeasible"),
        )
        for changes, included, excluded in cases:
            with self.subTest(changes=changes):
                message = evidence_explanation(self.opportunity(**changes))
                self.assertIn(included, message)
                if excluded:
                    self.assertNotIn(excluded, message.lower())
                self.assertNotIn("engineering feasibility", message.lower())
                self.assertNotIn("verify_presence", message)

    def test_dashboard_and_direct_links_keep_entry_and_focus_separate(self):
        dashboard = (ROOT / "src/dashboard/templates/dashboard.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("Review a seating opportunity", dashboard)
        self.assertNotIn("campaign=presence_verification", dashboard)
        self.assertIn("What would help next", dashboard)
        for relative in (
            "src/dashboard/static/stop_detail.js",
            "scripts/active/build_stop_profile_page.py",
        ):
            source = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("mode=direct", source)
        map_source = (ROOT / "src/dashboard/static/dashboard.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("mode=map", map_source)

    def test_normal_volunteer_surfaces_are_coherent(self):
        dashboard = (ROOT / "src/dashboard/templates/dashboard.html").read_text(
            encoding="utf-8"
        )
        self.assertEqual(1, dashboard.count("/review/start?mode=opportunity"))
        self.assertIn("/review/start?mode=route", dashboard)
        self.assertIn('id="nearbyReviewLink"', dashboard)
        self.assertIn("Browse the map", dashboard)
        self.assertIn("Explore by jurisdiction", dashboard)
        self.assertIn('id="pipelineSearch"', dashboard)

        review_info = (ROOT / "src/dashboard/static/review_info_loader.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("Why you're reviewing this stop", review_info)
        self.assertIn("What would be useful to check", review_info)
        self.assertNotIn("Why this stop was selected", review_info)
        self.assertNotIn("Documented need index", review_info)
        self.assertNotIn("review_priority_score", review_info)
        self.assertNotIn("Assignment:", review_info)

        stop_detail = (ROOT / "src/dashboard/static/stop_detail.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("How this opportunity was assessed", stop_detail)
        self.assertIn("Street View imagery captured", stop_detail)
        self.assertNotIn("Documented need index", stop_detail)

    def test_survey_and_completion_explain_provenance_and_contribution(self):
        survey = (ROOT / "src/review/community_survey_v1.py").read_text(
            encoding="utf-8"
        )
        self.assertIn("may differ from today's review date", survey)
        self.assertIn("preliminary visual observation", survey)
        self.assertIn("Path appears blocked", survey)

        review_page = (ROOT / "src/dashboard/templates/review.html").read_text(
            encoding="utf-8"
        )
        self.assertIn("added to this stop's history", review_page)
        self.assertIn("dated piece of evidence", review_page)
        self.assertIn("help build the case for", review_page)
        self.assertIn("property-owner follow-up", review_page)
        self.assertIn("does not make you the stop owner", review_page)
        self.assertIn("View this stop's updated record", review_page)

        map_source = (ROOT / "src/dashboard/static/dashboard.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("What we currently know", map_source)
        self.assertIn("A current observation would help improve this record", map_source)

    def test_review_page_puts_orientation_exposure_and_conflicts_up_front(self):
        source = (ROOT / "src/dashboard/static/review_info_loader.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("Serving direction", source)
        self.assertIn("Rider exposure:", source)
        self.assertIn("Route-based rider exposure", source)
        self.assertIn("renderCanonicalStatuses", source)
        evidence_ui = (ROOT / "src/dashboard/static/local_evidence.js").read_text(encoding="utf-8")
        self.assertIn("OpenStreetMap", evidence_ui)
        self.assertIn("DDOT shelter asset record", evidence_ui)
        self.assertIn("Source record:", evidence_ui)
        self.assertNotIn("engineering, accessibility compliance, ownership", source)
        self.assertIn("preliminary visual check", source)

    def test_canonical_provenance_distinguishes_explicit_osm_from_missing(self):
        from src.api.app import build_amenity_status_payload
        base = ("bench", "likely_no", "not_reached", 0, 0, "[]", None,
                "[]", "[]", 0, 1, 0, 0)
        shown = build_amenity_status_payload([base], [])[0]["contributing_evidence"]
        self.assertEqual([{"source": "OPENSTREETMAP", "claim": "absent",
                           "kind": "osm", "explicit": True}], shown)
        missing = list(base)
        missing[10] = 0
        self.assertEqual([], build_amenity_status_payload([tuple(missing)], [])[0]["contributing_evidence"])

    def test_view_stop_details_uses_human_page_not_api(self):
        page = (ROOT / "src/dashboard/templates/review.html").read_text(encoding="utf-8")
        assignment = page[page.index("viewStopDetailsButton.href"):]
        self.assertIn("`/stop/${reviewStopId}`", assignment)
        self.assertNotIn("`/stops/${reviewStopId}`", assignment)

    def test_only_two_current_review_modes_are_offered_and_legacy_is_readable(self):
        from src.review.community_survey_v1 import SURVEY
        self.assertEqual({"in_person", "remote"}, {
            value for value, _ in SURVEY["review_mode"]["options"]
        })
        loader = (ROOT / "src/dashboard/static/review_info_loader.js").read_text(encoding="utf-8")
        self.assertIn('street_view: "Remote (Street View)"', loader)
        self.assertIn('other_remote_visual: "Remote (visual source)"', loader)
        survey_js = (ROOT / "src/dashboard/static/review_survey.js").read_text(encoding="utf-8")
        self.assertIn('mode === "remote"', survey_js)
        page = (ROOT / "src/dashboard/templates/review.html").read_text(encoding="utf-8")
        self.assertIn('selectedMode === "remote"', page)


if __name__ == "__main__":
    unittest.main()

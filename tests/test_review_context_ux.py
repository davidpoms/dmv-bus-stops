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
            "opportunity": "Opportunity Review selected this stop",
            "route": "route you chose to review",
            "nearby": "stops near you",
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


if __name__ == "__main__":
    unittest.main()

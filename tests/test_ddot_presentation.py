import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DdotPresentationTests(unittest.TestCase):
    def test_stop_renderers_use_clean_ddot_evidence_in_local_section(self):
        source = (ROOT / "src/dashboard/static/local_evidence.js").read_text(
            encoding="utf-8"
        )
        self.assertIn('DDOT_ARCGIS: "DDOT shelter asset record"', source)
        self.assertIn('DISTRICT_OF_COLUMBIA: "District of Columbia"', source)
        self.assertIn('evidence.source !== "DDOT"', source)

    def test_legacy_ddot_card_renderer_is_removed(self):
        source = (ROOT / "src/dashboard/static/stop_detail.js").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("const ddotEvidenceHtml", source)
        self.assertNotIn("DDOT shelter procurement inventory", source)


if __name__ == "__main__":
    unittest.main()

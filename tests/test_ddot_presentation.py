import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DdotPresentationTests(unittest.TestCase):
    def test_stop_renderers_use_clean_ddot_evidence_in_local_section(self):
        for relative_path in (
            "src/dashboard/static/stop_detail.js",
            "src/dashboard/static/review_info_loader.js",
        ):
            with self.subTest(path=relative_path):
                source = (ROOT / relative_path).read_text(encoding="utf-8")
                self.assertIn('item.source === "DDOT_ARCGIS"' if "stop_detail" in relative_path
                              else 'evidence.source === "DDOT_ARCGIS"', source)
                self.assertIn("District of Columbia", source)
                self.assertIn("DDOT shelter asset record", source)
                self.assertNotIn('item.source === "DDOT"', source)

    def test_legacy_ddot_card_renderer_is_removed(self):
        source = (ROOT / "src/dashboard/static/stop_detail.js").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("const ddotEvidenceHtml", source)
        self.assertNotIn("DDOT shelter procurement inventory", source)


if __name__ == "__main__":
    unittest.main()

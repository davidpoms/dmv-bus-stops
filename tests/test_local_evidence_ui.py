import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RENDERER = ROOT / "src" / "dashboard" / "static" / "local_evidence.js"


class LocalEvidenceUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.renderer = RENDERER.read_text(encoding="utf-8")

    def test_all_supported_amenities_have_friendly_labels(self):
        expected = {
            "shelter": "Shelter", "bench": "Bench",
            "trash_can": "Trash can", "sign": "Sign",
            "ada_bus_pad": "ADA bus pad", "ada_path": "ADA path",
            "recycling": "Recycling", "bikerack": "Bike rack",
            "parking": "Parking", "streetlight": "Streetlight",
            "real_time_sign": "Real-time sign", "bus_bay": "Bus bay",
            "bus_bulb": "Bus bulb",
        }
        for amenity, label in expected.items():
            with self.subTest(amenity=amenity):
                self.assertIn(f'{amenity}: "{label}"', self.renderer)

    def test_jurisdiction_and_special_source_labels_are_friendly(self):
        labels = {
            "DISTRICT_OF_COLUMBIA": "District of Columbia",
            "PRINCE_GEORGES_COUNTY": "Prince George's County",
            "MONTGOMERY_COUNTY": "Montgomery County",
            "ARLINGTON_COUNTY": "Arlington County",
            "ALEXANDRIA": "City of Alexandria",
            "FAIRFAX_COUNTY": "Fairfax County",
            "PRINCE_GEORGES_COUNTY_THEBUS":
                "Prince George's County TheBus stop inventory",
            "DDOT_ARCGIS": "DDOT shelter asset record",
        }
        for internal, label in labels.items():
            with self.subTest(source=internal):
                self.assertIn(internal, self.renderer)
                self.assertIn(label, self.renderer)

    def test_grouping_keeps_source_records_distinct(self):
        self.assertIn('evidence.jurisdiction || ""', self.renderer)
        self.assertIn('evidence.source || ""', self.renderer)
        self.assertIn('evidence.source_record || ""', self.renderer)
        self.assertIn("groups.get(key).amenities.push(evidence)", self.renderer)
        self.assertIn("group.amenities.map", self.renderer)

    def test_negative_unknown_and_positive_values_are_explicit(self):
        self.assertIn('if (value === "yes") return "Yes"', self.renderer)
        self.assertIn('if (value === "no") return "No"', self.renderer)
        self.assertIn('evidence.present === 0', self.renderer)
        self.assertIn('return "Not recorded"', self.renderer)
        self.assertNotIn("evidence.present ?", self.renderer)

    def test_unknown_type_uses_escaped_generic_fallback(self):
        self.assertIn("AMENITY_LABELS[type] || genericLabel(type)", self.renderer)
        self.assertIn("escapeHtml(amenityLabel(evidence.amenity_type))", self.renderer)
        self.assertIn("escapeHtml(group.sourceRecord", self.renderer)

    def test_order_is_global_and_deterministic(self):
        positions = [self.renderer.index(f'        "{amenity}"') for amenity in (
            "shelter", "bench", "trash_can", "recycling", "sign",
            "real_time_sign", "ada_bus_pad", "ada_path", "bus_bay",
            "bus_bulb", "bikerack", "parking", "streetlight",
        )]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("localeCompare(String(right.amenity_type", self.renderer)

    def test_raw_data_and_legacy_ddot_are_not_rendered(self):
        self.assertIn('evidence.source !== "DDOT"', self.renderer)
        self.assertNotIn("raw_value", self.renderer)
        self.assertNotIn("source_metadata", self.renderer)
        self.assertNotIn("jurisdiction_source_evidence", self.renderer)
        self.assertNotIn("BSTP_HAS_", self.renderer)

    def test_both_pages_use_shared_renderer_and_keep_community_sections(self):
        for path in (
            ROOT / "src/dashboard/static/stop_detail.js",
            ROOT / "src/dashboard/static/review_info_loader.js",
        ):
            source = path.read_text(encoding="utf-8")
            self.assertIn("LocalEvidenceUI.render", source)
            self.assertIn("Community observations", source)
            self.assertNotIn('amenity_type === "shelter"', source)
            self.assertNotIn('amenity_type === "bench"', source)

    def test_public_payload_does_not_include_raw_fields(self):
        source = (ROOT / "src/api/app.py").read_text(encoding="utf-8")
        payload = source[source.index("amenity_evidence_payload = ["):]
        payload = payload[:payload.index("return jsonify")]
        self.assertNotIn('"raw_value"', payload)
        self.assertNotIn('"source_metadata"', payload)
        self.assertNotIn("jurisdiction_source_evidence", payload)


if __name__ == "__main__":
    unittest.main()

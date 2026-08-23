import subprocess
import sys
import unittest
from pathlib import Path

from src.assessment.interpretation import interpret_ddot_evidence, summarize_stop_evidence


ROOT = Path(__file__).resolve().parents[1]


class LegacyQuarantineTests(unittest.TestCase):
    def test_legacy_scripts_fail_before_execution(self):
        for relative_path in (
            "scripts/reconcile_ddot_route_evidence.py",
            "scripts/import_ddot_shelter_evidence.py",
            "scripts/normalize_ddot_shelter_amenities.py",
        ):
            result = subprocess.run(
                [sys.executable, str(ROOT / relative_path)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(0, result.returncode, relative_path)
            self.assertIn("QUARANTINED LEGACY PATH", result.stderr + result.stdout)

    def test_legacy_confirmed_active_is_not_current_authority(self):
        records = [{"lifecycle_status": "CONFIRMED_ACTIVE", "ddot_id": "1000087"}]
        interpreted = interpret_ddot_evidence(records)
        self.assertEqual("quarantined_legacy", interpreted[0]["evidence_class"])
        self.assertNotIn("Verified", interpreted[0]["public_status"])

        summary = summarize_stop_evidence({"ddot": records})
        self.assertFalse(summary["ddot_shelter"]["confirmed_active"])


if __name__ == "__main__":
    unittest.main()

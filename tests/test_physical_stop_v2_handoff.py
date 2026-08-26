import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class HandoffTests(unittest.TestCase):
    def test_frozen_contamination_and_manual_sets(self):
        text=(ROOT/'docs/physical-stop-identity-v2.md').read_text(encoding='utf-8')
        for stop in (506,658,1437,1917,2340,2451,3313,3752,3802,4088,4563):
            self.assertIn(str(stop),text)
        for stop in (406,2231,4468,5196,6080): self.assertIn(str(stop),text)
        self.assertIn('384 affected parents',text)
        self.assertIn('791 proposed child',text)
    def test_reference_resolved_splits_are_frozen(self):
        text=(ROOT/'docs/physical-stop-identity-v2.md').read_text(encoding='utf-8')
        for stop in (82,2048,3021): self.assertIn(str(stop),text)
        serving=(ROOT/'docs/serving-directions.md').read_text(encoding='utf-8')
        self.assertIn('Stop 935',serving)
if __name__=='__main__':unittest.main()

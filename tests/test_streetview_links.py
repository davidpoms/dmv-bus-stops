"""Guard the optional imagery action and independent stop-location fallback."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class StreetViewLinkTests(unittest.TestCase):
    def test_review_maps_action_precedes_optional_imagery(self):
        source = (ROOT / 'src/dashboard/static/review_info_loader.js').read_text(encoding='utf-8')
        self.assertIn('encodeURIComponent(`${info.lat},${info.lon}`)', source)
        self.assertLess(source.index('Open in Google Maps'), source.index('Try Street View'))
        self.assertIn('info.streetview_url ?', source)
        self.assertIn('Street View imagery may be unavailable', source)
        self.assertIn('review in person or with another visual source', source)

    def test_stop_maps_action_is_independent_of_panorama(self):
        source = (ROOT / 'src/dashboard/static/stop_detail.js').read_text(encoding='utf-8')
        self.assertIn('encodeURIComponent(`${stop.lat},${stop.lon}`)', source)
        self.assertLess(source.index('Open in Google Maps'), source.index('Try Street View'))
        self.assertIn('${streetview ?', source)
        self.assertIn('Street View imagery may be unavailable', source)


if __name__ == '__main__':
    unittest.main()

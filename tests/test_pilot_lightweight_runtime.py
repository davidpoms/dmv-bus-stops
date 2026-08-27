import os
import subprocess
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


class PilotLightweightRuntimeTests(unittest.TestCase):
    def test_app_import_does_not_require_numpy_or_scipy(self):
        source = """
import builtins
original = builtins.__import__
def guarded(name, *args, **kwargs):
    if name == 'numpy' or name.startswith('scipy'):
        raise ModuleNotFoundError(name)
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
from src.api.app import app
assert app is not None
assert 'src.spatial.nearest_road' not in __import__('sys').modules
"""
        environment = os.environ.copy()
        environment["FLASK_SECRET_KEY"] = "lightweight-runtime-import-test"
        result = subprocess.run(
            [sys.executable, "-c", source], cwd=ROOT, env=environment,
            text=True, capture_output=True,
        )
        self.assertEqual(0, result.returncode, result.stderr)

    def test_road_index_lazily_imports_and_uses_engine(self):
        from src.api import app as api

        seen = []

        class FakeRoadSpatialIndex:
            def __init__(self, roads):
                seen.extend(roads)

            def nearest_road(self, lat, lon):
                return {"lat": lat, "lon": lon}

        fake_module = types.ModuleType("src.spatial.nearest_road")
        fake_module.RoadSpatialIndex = FakeRoadSpatialIndex
        api.road_index = None
        self.addCleanup(setattr, api, "road_index", None)
        rows = [('{"coordinates":[[-77.0,38.9],[-77.1,39.0]]}', "primary")]
        with patch.dict(sys.modules, {"src.spatial.nearest_road": fake_module}), \
                patch.object(api, "query_db", return_value=rows):
            index = api.get_road_index()
        self.assertEqual("primary", seen[0]["road_class"])
        self.assertEqual({"lat": 38.9, "lon": -77.0}, index.nearest_road(38.9, -77.0))

    def test_road_index_failure_keeps_empty_fallback(self):
        from src.api import app as api

        class BrokenRoadSpatialIndex:
            def __init__(self, _roads):
                raise RuntimeError("fixture failure")

        fake_module = types.ModuleType("src.spatial.nearest_road")
        fake_module.RoadSpatialIndex = BrokenRoadSpatialIndex
        api.road_index = None
        self.addCleanup(setattr, api, "road_index", None)
        rows = [('{"coordinates":[[-77.0,38.9],[-77.1,39.0]]}', "primary")]
        with patch.dict(sys.modules, {"src.spatial.nearest_road": fake_module}), \
                patch.object(api, "query_db", return_value=rows), \
                patch.object(api.app.logger, "exception") as logged:
            index = api.get_road_index()
        self.assertIsNone(index.nearest_road(38.9, -77.0))
        logged.assert_called_once_with("road_centerline_index_build_failed")


if __name__ == "__main__":
    unittest.main()

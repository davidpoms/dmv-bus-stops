import os
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "src" / "api" / "app.py"


class ApiDatabasePathTests(unittest.TestCase):
    def imported_database_path(self, override=None):
        env = os.environ.copy()
        if override is None:
            env.pop("DMV_BUS_STOPS_DB", None)
        else:
            env["DMV_BUS_STOPS_DB"] = str(override)
        output = subprocess.check_output(
            [
                sys.executable,
                "-c",
                "from src.api.app import DATABASE_PATH; print(DATABASE_PATH)",
            ],
            cwd=ROOT,
            env=env,
            text=True,
        )
        return Path(output.strip())

    def test_default_database_path_remains_repo_relative(self):
        self.assertEqual(
            ROOT / "src" / "database" / "dmv_bus_stops.db",
            self.imported_database_path(),
        )

    def test_environment_override_is_honored(self):
        override = ROOT / "configured" / "override.db"
        self.assertEqual(override, self.imported_database_path(override))

    def test_app_has_no_cwd_relative_production_database_literal(self):
        source = APP_PATH.read_text(encoding="utf-8")
        self.assertNotIn('sqlite3.connect("src/database/dmv_bus_stops.db")', source)
        self.assertNotIn('"src/database/dmv_bus_stops.db"', source)


if __name__ == "__main__":
    unittest.main()

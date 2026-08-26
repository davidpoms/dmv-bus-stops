import unittest
from pathlib import Path

from src.api.app import app


ROOT = Path(__file__).resolve().parents[1]


class PilotReadinessTests(unittest.TestCase):
    def test_local_env_loads_before_database_consumers_without_secret_fallback(self):
        source = (ROOT / "src/api/app.py").read_text(encoding="utf-8")
        self.assertLess(
            source.index('load_dotenv(BASE_DIR / ".env")'),
            source.index("from src.review.assignment_router import"),
        )
        self.assertIn('os.environ.get("FLASK_SECRET_KEY")', source)
        self.assertNotIn("FLASK_SECRET_KEY or", source)

    def test_env_example_is_trackable_while_real_envs_are_ignored(self):
        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn(".env.*", ignore)
        self.assertIn("!.env.example", ignore)
        example = (ROOT / ".env.example").read_text(encoding="utf-8")
        self.assertIn("replace-with-a-persistent-local-only-random-value", example)
        self.assertIn("must never be enabled", (
            ROOT / "docs/LOCAL_DEVELOPMENT.md"
        ).read_text(encoding="utf-8"))

    def test_primary_human_routes_and_json_stop_api_are_distinct(self):
        rules = {rule.rule: rule.endpoint for rule in app.url_map.iter_rules()}
        self.assertEqual("stop_page", rules["/stop/<int:stop_id>"])
        self.assertEqual("stop_detail", rules["/stops/<int:stop_id>"])
        dashboard = (ROOT / "src/dashboard/static/dashboard.js").read_text(
            encoding="utf-8"
        )
        self.assertIn('href="/stop/${props.stop_id}"', dashboard)
        self.assertNotIn('href="/stops/${props.stop_id}"', dashboard)

    def test_runbooks_separate_active_archive_local_and_production(self):
        archive = (ROOT / "scripts/archive/README.md").read_text(encoding="utf-8")
        local = (ROOT / "docs/LOCAL_DEVELOPMENT.md").read_text(encoding="utf-8")
        pilot = (ROOT / "docs/PILOT_READINESS.md").read_text(encoding="utf-8")
        self.assertIn("not a supported executable migration set", archive)
        self.assertIn("Flask's built-in server", local)
        self.assertIn("production deployment server", local)
        self.assertIn("Physical-stop identity", pilot)
        self.assertIn("Feedback mechanism", pilot)


if __name__ == "__main__":
    unittest.main()

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import generate_improvement_recommendations as legacy_recommendations
from scripts import generate_priority_levels
from src.assessment import create_opportunity_assessments
from src.assessment import generate_impact_summary
from src.assessment import generate_improvement_recommendations
from src.assessment import score_improvement_opportunities
from src.scoring import calculate_stop_priority


class ActiveStopPipelineTests(unittest.TestCase):
    def setUp(self):
        handle = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        handle.close()
        self.db = Path(handle.name)
        conn = sqlite3.connect(self.db)
        conn.executescript(
            """
            CREATE TABLE physical_stops (id INTEGER PRIMARY KEY);
            INSERT INTO physical_stops VALUES (1), (2), (3);
            CREATE TABLE stop_gtfs_status (
                physical_stop_id INTEGER PRIMARY KEY,
                current_gtfs INTEGER NOT NULL
            );
            INSERT INTO stop_gtfs_status VALUES (1, 1), (2, 0);
            CREATE TABLE stop_jurisdiction (
                stop_id INTEGER, state TEXT, county TEXT
            );
            INSERT INTO stop_jurisdiction VALUES
                (1,'DC',NULL),(2,'DC',NULL),(3,'DC',NULL);

            CREATE TABLE physical_stop_members (
                physical_stop_id INTEGER, bus_stop_id INTEGER
            );
            INSERT INTO physical_stop_members VALUES (1, 101), (2, 102), (3, 103);
            CREATE TABLE stop_routes (
                id INTEGER PRIMARY KEY, stop_id INTEGER, route_id INTEGER
            );
            INSERT INTO stop_routes VALUES (1,101,10), (2,102,10), (3,103,10);
            CREATE TABLE routes (id INTEGER PRIMARY KEY, route_id TEXT);
            INSERT INTO routes VALUES (10, 'A1');
            CREATE TABLE ridership_snapshots (
                route_id TEXT, weekday_boardings REAL, period TEXT
            );
            INSERT INTO ridership_snapshots VALUES ('A1', 2300, '2026-07-01');

            CREATE TABLE stop_priority_snapshots (
                id INTEGER PRIMARY KEY, stop_id INTEGER, priority_score REAL,
                priority_rank INTEGER, factors TEXT,
                calculated_date TEXT DEFAULT CURRENT_TIMESTAMP
            );
            INSERT INTO stop_priority_snapshots (stop_id, factors) VALUES
                (2, '{"route_exposure_score":100}'),
                (3, '{"route_exposure_score":100}');
            CREATE TABLE opportunity_assessments (
                id INTEGER PRIMARY KEY, physical_stop_id INTEGER,
                combined_route_weekday_boardings REAL,
                highest_route_weekday_boardings REAL, routes_served INTEGER,
                wmata_stop_records INTEGER, assessment_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            INSERT INTO opportunity_assessments (physical_stop_id) VALUES (2), (3);
            CREATE TABLE improvement_opportunities (
                id INTEGER PRIMARY KEY, physical_stop_id INTEGER,
                opportunity_score REAL, priority_rank INTEGER, factors TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            INSERT INTO improvement_opportunities (physical_stop_id,opportunity_score,factors)
                VALUES (2,99,'{}'), (3,100,'{}');
            CREATE TABLE stop_osm_evidence (
                stop_id INTEGER, osm_bench INTEGER, osm_shelter INTEGER
            );
            INSERT INTO stop_osm_evidence VALUES (1,0,0),(2,0,0),(3,0,0);
            CREATE TABLE stop_amenity_evidence (
                physical_stop_id INTEGER, source TEXT, amenity_type TEXT,
                present INTEGER, confidence TEXT
            );
            CREATE TABLE stop_transit_evidence (stop_id INTEGER, gtfs_bus_stop INTEGER);
            INSERT INTO stop_transit_evidence VALUES (1,1),(2,1),(3,1);
            CREATE TABLE stop_consensus (
                stop_id INTEGER, has_bench INTEGER, has_shelter INTEGER,
                ada_accessible INTEGER, confidence REAL,
                seating_type_consensus TEXT, rider_comfort_consensus TEXT,
                hostile_design_consensus TEXT, bench_feasible INTEGER,
                reviewer_count INTEGER, consensus_status TEXT
            );
            INSERT INTO stop_consensus VALUES
                (1,0,0,1,1.0,NULL,NULL,NULL,1,2,'verified'),
                (2,0,0,1,1.0,NULL,NULL,NULL,1,2,'verified'),
                (3,0,0,1,1.0,NULL,NULL,NULL,1,2,'verified');
            CREATE TABLE stop_amenity_status (
                physical_stop_id INTEGER, amenity_type TEXT,
                derived_status TEXT, consensus_status TEXT,
                community_observation_count INTEGER,
                community_no_count INTEGER, osm_no INTEGER
            );
            INSERT INTO stop_amenity_status VALUES
                (1,'bench','conflicting','not_reached',1,0,0),
                (1,'shelter','conflicting','not_reached',1,0,0);
            CREATE TABLE stop_observations (
                id INTEGER PRIMARY KEY, physical_stop_id INTEGER, source TEXT,
                bench_feasible TEXT
            );
            INSERT INTO stop_observations VALUES
                (1,1,'community_review',NULL),(2,2,'community_review',NULL),
                (3,3,'community_review',NULL);
            CREATE TABLE improvement_recommendations (
                id INTEGER PRIMARY KEY, physical_stop_id INTEGER,
                recommendation_type TEXT, priority TEXT, reasons TEXT,
                confidence TEXT, evidence TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            INSERT INTO improvement_recommendations
                (physical_stop_id,recommendation_type,priority)
                VALUES (2,'stale','high'),(3,'stale','high');
            CREATE TABLE stop_improvement_impact (
                id INTEGER PRIMARY KEY, physical_stop_id INTEGER,
                daily_route_exposure REAL, average_weekday_boardings REAL,
                opportunity_score REAL, impact_level TEXT,
                recommendations TEXT, summary TEXT, priority_level TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            INSERT INTO stop_improvement_impact (physical_stop_id,opportunity_score)
                VALUES (2,99),(3,100);
            """
        )
        conn.commit()
        conn.close()

    def tearDown(self):
        try:
            self.db.unlink(missing_ok=True)
        except PermissionError:
            # A failed SQLite assertion can leave a connection pending until
            # garbage collection on Windows; successful runs remove it.
            pass

    def ids(self, table, column="physical_stop_id"):
        conn = sqlite3.connect(self.db)
        values = {row[0] for row in conn.execute(f"SELECT {column} FROM {table}")}
        conn.close()
        return values

    def test_every_scoped_generator_names_the_canonical_invariant(self):
        root = Path(__file__).resolve().parents[1]
        paths = (
            "src/scoring/calculate_stop_priority.py",
            "src/assessment/create_opportunity_assessments.py",
            "src/assessment/score_improvement_opportunities.py",
            "src/assessment/generate_improvement_recommendations.py",
            "src/assessment/generate_impact_summary.py",
            "src/assessment/create_project_priorities.py",
            "src/assessment/calculate_recommendation_confidence.py",
            "scripts/generate_improvement_recommendations.py",
            "scripts/generate_priority_levels.py",
        )
        for relative_path in paths:
            with self.subTest(path=relative_path):
                source = (root / relative_path).read_text(encoding="utf-8")
                self.assertIn("stop_gtfs_status", source)
                self.assertIn("current_gtfs = 1", source)

    def test_core_rebuilds_fail_closed_despite_identical_proxy_evidence(self):
        patches = (
            patch.object(calculate_stop_priority, "DATABASE_PATH", self.db),
            patch.object(create_opportunity_assessments, "DATABASE_PATH", self.db),
            patch.object(score_improvement_opportunities, "DATABASE_PATH", self.db),
            patch.object(generate_improvement_recommendations, "DATABASE_PATH", self.db),
            patch.object(generate_impact_summary, "DATABASE_PATH", self.db),
        )
        for context in patches:
            context.start()
            self.addCleanup(context.stop)

        calculate_stop_priority.calculate_scores()
        self.assertEqual({1}, self.ids("stop_priority_snapshots", "stop_id"))

        create_opportunity_assessments.create_assessments()
        self.assertEqual({1}, self.ids("opportunity_assessments"))

        score_improvement_opportunities.score_opportunities()
        self.assertEqual({1}, self.ids("improvement_opportunities"))

        generate_improvement_recommendations.generate_recommendations()
        self.assertEqual({1}, self.ids("improvement_recommendations"))

        generate_impact_summary.generate_impact_summary()
        self.assertEqual({1}, self.ids("stop_improvement_impact"))

        # A stale high-scoring row cannot affect the active percentile pool.
        conn = sqlite3.connect(self.db)
        conn.execute(
            "INSERT INTO stop_improvement_impact "
            "(physical_stop_id,opportunity_score) VALUES (2,1000)"
        )
        conn.commit()
        conn.close()
        generate_priority_levels.generate_priority_levels(self.db)
        self.assertEqual({1}, self.ids("stop_improvement_impact"))

        # The older directly-invoked generator is also fail-closed.
        legacy_recommendations.generate_recommendations(self.db)
        self.assertEqual({1}, self.ids("improvement_recommendations"))

        # Historical evidence/proxy inputs are retained for all three stops.
        self.assertEqual({1, 2, 3}, self.ids("stop_observations"))
        self.assertEqual({1, 2, 3}, self.ids("stop_transit_evidence", "stop_id"))


if __name__ == "__main__":
    unittest.main()

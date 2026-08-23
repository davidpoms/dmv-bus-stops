import sqlite3
from pathlib import Path

DB = Path("src/database/dmv_bus_stops.db")

conn = sqlite3.connect(DB)
cur = conn.cursor()


cur.execute("""
CREATE TABLE IF NOT EXISTS stop_osm_evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stop_id INTEGER NOT NULL,
    osm_bus_stop INTEGER DEFAULT 0,
    osm_bench INTEGER DEFAULT 0,
    osm_shelter INTEGER DEFAULT 0,
    osm_feature_id TEXT,
    osm_tags TEXT,
    osm_snapshot_date TEXT,
    osm_source_file TEXT
)
""")


cur.execute("""
CREATE TABLE IF NOT EXISTS stop_transit_evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stop_id INTEGER NOT NULL,
    gtfs_bus_stop INTEGER DEFAULT 0,
    route_count INTEGER DEFAULT 0,
    source TEXT
)
""")


cur.execute("""
CREATE TABLE IF NOT EXISTS stop_wmata_evidence (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    physical_stop_id INTEGER,
    wmata_stop_id TEXT,
    wmata_status TEXT,
    wmata_heading TEXT,
    wmata_bench INTEGER DEFAULT 0,
    wmata_shelter INTEGER DEFAULT 0,
    wmata_accessible TEXT,
    match_distance_m REAL,
    match_confidence TEXT,
    source TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")


cur.execute("""
CREATE TABLE IF NOT EXISTS stop_consensus (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stop_id INTEGER NOT NULL,
    has_bench INTEGER,
    has_shelter INTEGER,
    ada_accessible INTEGER,
    confidence REAL DEFAULT 0,
    seating_type_consensus TEXT,
    rider_comfort_consensus TEXT,
    hostile_design_consensus TEXT,
    bench_feasible INTEGER
)
""")


conn.commit()
conn.close()

print("Evidence schema created.")
from pathlib import Path
import re

p = Path("src/database/schema.sql")
text = p.read_text()

pattern = r"CREATE TABLE IF NOT EXISTS stop_reviews\s*\(.*?\n\);"

replacement = """
CREATE TABLE IF NOT EXISTS stop_observations (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    physical_stop_id INTEGER NOT NULL,

    observer TEXT,

    shelter_present TEXT,

    bench_present TEXT,

    trash_present TEXT,

    bench_feasible TEXT,

    ada_clearance_possible TEXT,

    notes TEXT,

    observed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    source TEXT DEFAULT 'unknown',

    reviewer_id INTEGER,

    confidence REAL,

    streetview_checked BOOLEAN,

    osm_checked BOOLEAN,

    FOREIGN KEY(physical_stop_id)
        REFERENCES physical_stops(id)

);
"""

text, count = re.subn(pattern, replacement, text, flags=re.S)

p.write_text(text)

print(f"Replaced {count} stop_reviews table definitions")

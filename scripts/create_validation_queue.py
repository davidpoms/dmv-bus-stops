import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS stop_validation (
    physical_stop_id INTEGER PRIMARY KEY,
    status TEXT DEFAULT 'needs_validation',
    validator TEXT,
    notes TEXT,
    validated_at TEXT
)
""")

cur.execute("""
INSERT OR IGNORE INTO stop_validation (physical_stop_id)
SELECT physical_stop_id
FROM stop_improvement_impact
WHERE priority_level IN ('P1','P2','P3')
""")

conn.commit()

count = cur.execute("""
SELECT COUNT(*)
FROM stop_validation
""").fetchone()[0]

conn.close()

print(f"Validation queue created: {count} stops")

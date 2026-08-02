import sqlite3

conn = sqlite3.connect(
    "src/database/dmv_bus_stops.db"
)

c = conn.cursor()

rows = c.execute("""
SELECT
    s.stop_id,
    s.priority_score,
    io.opportunity_score
FROM stop_priority_snapshots s

JOIN improvement_opportunities io
    ON s.stop_id = io.physical_stop_id

WHERE s.stop_id = 2685;
""").fetchall()

print(rows)
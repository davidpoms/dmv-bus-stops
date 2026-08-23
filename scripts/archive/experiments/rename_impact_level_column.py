import sqlite3
from pathlib import Path

DB = Path("src/database/dmv_bus_stops.db")

conn = sqlite3.connect(DB)
cursor = conn.cursor()

cursor.execute("""
PRAGMA table_info(stop_improvement_impact);
""")

columns = {row[1] for row in cursor.fetchall()}

if "impact_level" in columns:
    cursor.execute("""
        UPDATE stop_improvement_impact
        SET priority_level = impact_level
        WHERE priority_level IS NULL;
    """)

    print("Copied impact_level values into priority_level")
else:
    print("impact_level already removed or missing")

conn.commit()
conn.close()

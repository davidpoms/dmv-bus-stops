import sqlite3
from pathlib import Path

DB = Path("src/database/dmv_bus_stops.db")

conn = sqlite3.connect(DB)
cursor = conn.cursor()

cursor.execute("""
PRAGMA table_info(stop_improvement_impact);
""")

columns = [row[1] for row in cursor.fetchall()]

if "daily_route_exposure" not in columns:
    if "daily_riders" in columns:
        cursor.execute("""
        ALTER TABLE stop_improvement_impact
        RENAME COLUMN daily_riders TO daily_route_exposure;
        """)
        print("Renamed daily_riders -> daily_route_exposure")
    else:
        cursor.execute("""
        ALTER TABLE stop_improvement_impact
        ADD COLUMN daily_route_exposure REAL;
        """)
        print("Added daily_route_exposure column")
else:
    print("daily_route_exposure already exists")

conn.commit()
conn.close()

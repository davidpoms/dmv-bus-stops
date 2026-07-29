import sqlite3
from pathlib import Path

DB = Path("src/database/dmv_bus_stops.db")

conn = sqlite3.connect(DB)
cur = conn.cursor()

columns = [
    ("seating_type_consensus", "TEXT"),
    ("rider_comfort_consensus", "TEXT"),
    ("hostile_design_consensus", "TEXT"),
]

for name, dtype in columns:
    try:
        cur.execute(
            f"""
            ALTER TABLE stop_consensus
            ADD COLUMN {name} {dtype};
            """
        )
        print("Added", name)

    except sqlite3.OperationalError:
        print("Already exists:", name)

conn.commit()
conn.close()

print("✓ Consensus comfort fields added")

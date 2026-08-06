import sqlite3
from pathlib import Path

DB = Path("src/database/dmv_bus_stops.db")

conn = sqlite3.connect(DB)
cursor = conn.cursor()

cursor.execute("""
PRAGMA table_info(project_priorities);
""")

columns = {row[1] for row in cursor.fetchall()}

print("Existing columns:", columns)

if "priority_level" not in columns:
    cursor.execute("""
        ALTER TABLE project_priorities
        ADD COLUMN priority_level TEXT;
    """)

    if "impact_level" in columns:
        cursor.execute("""
            UPDATE project_priorities
            SET priority_level = impact_level
            WHERE priority_level IS NULL;
        """)

    print("Added priority_level column")

else:
    print("priority_level already exists")

conn.commit()
conn.close()

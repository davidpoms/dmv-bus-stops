import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)

try:
    conn.execute(
        """
        ALTER TABLE community_reviewers
        ADD COLUMN display_name TEXT
        """
    )

    conn.commit()

    print("Added display_name column")

except sqlite3.OperationalError as e:
    print("Migration skipped:", e)

finally:
    conn.close()
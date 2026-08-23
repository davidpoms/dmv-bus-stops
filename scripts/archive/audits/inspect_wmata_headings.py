import sqlite3

conn = sqlite3.connect(
    "src/database/dmv_bus_stops.db"
)

cur = conn.cursor()

print("Stop 2772:")
print(
    cur.execute(
        """
        SELECT
            physical_stop_id,
            wmata_heading
        FROM stop_wmata_evidence
        WHERE physical_stop_id = 2772
        """
    ).fetchone()
)


print("\nSample headings:")

rows = cur.execute(
    """
    SELECT
        physical_stop_id,
        wmata_heading
    FROM stop_wmata_evidence
    WHERE wmata_heading IS NOT NULL
    LIMIT 20
    """
).fetchall()


for row in rows:
    print(row)


conn.close()
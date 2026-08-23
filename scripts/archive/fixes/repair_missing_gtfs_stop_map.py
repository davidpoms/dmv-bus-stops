import sqlite3
from pathlib import Path
from datetime import datetime


DB = Path("src/database/dmv_bus_stops.db")


conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
c = conn.cursor()


backup = DB.with_name(
    f"before_gtfs_stop_map_repair_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
)

print("Creating backup:", backup)

dest = sqlite3.connect(backup)
conn.backup(dest)
dest.close()



print("\nBefore:")
print(
    c.execute(
        "SELECT COUNT(*) FROM gtfs_stop_map"
    ).fetchone()[0]
)



missing = c.execute(
"""
SELECT DISTINCT
    srb.stop_id

FROM stop_routes_backup srb

LEFT JOIN gtfs_stop_map gm
    ON CAST(srb.stop_id AS TEXT)=gm.gtfs_stop_id

WHERE gm.gtfs_stop_id IS NULL
"""
).fetchall()



print("\nMissing GTFS ids:", len(missing))


recovered = 0
unresolved = []


for row in missing:

    gtfs_id = str(row["stop_id"])


    match = c.execute(
    """
    SELECT id
    FROM bus_stops
    WHERE external_stop_id=?
    """,
    (gtfs_id,)
    ).fetchone()


    if match:

        c.execute(
        """
        INSERT OR IGNORE INTO gtfs_stop_map
        (
            gtfs_stop_id,
            bus_stop_id,
            match_distance,
            match_method
        )
        VALUES
        (?, ?, ?, ?)
        """,
        (
            gtfs_id,
            match["id"],
            0,
            "external_stop_id_recovery"
        )
        )

        recovered += 1

    else:

        unresolved.append(gtfs_id)



conn.commit()



print("\nRecovered mappings:", recovered)


print("\nStill unresolved:", len(unresolved))

for x in unresolved:
    print(x)



print("\nAfter:")
print(
    c.execute(
        "SELECT COUNT(*) FROM gtfs_stop_map"
    ).fetchone()[0]
)



conn.close()

print("\nDone.")
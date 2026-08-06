import sqlite3


DB = "src/database/dmv_bus_stops.db"


TEST_IDS = [
    "1001352",
    "1001399",
    "1000694",
    "1001294",
]


conn = sqlite3.connect(DB)

conn.row_factory = sqlite3.Row


print("Testing GTFS IDs...")


for stop_id in TEST_IDS:

    print("\nSTOP:", stop_id)

    rows = conn.execute(
        """
        SELECT
            b.id,
            b.external_stop_id,
            b.stop_name,
            psm.physical_stop_id
        FROM bus_stops b
        LEFT JOIN physical_stop_members psm
        ON b.id = psm.bus_stop_id
        WHERE b.external_stop_id=?
        """,
        (stop_id,)
    ).fetchall()


    if not rows:
        print("  NOT FOUND IN bus_stops")
        continue


    for r in rows:
        print(dict(r))


conn.close()
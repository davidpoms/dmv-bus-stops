import sqlite3


DB = "src/database/dmv_bus_stops.db"


missing_ids = [
    "1001352",
    "1001399",
    "1000694",
    "1001294",
    "1002483",
    "1001433",
    "1002295",
]


conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row


for ddot_id in missing_ids:

    print("\nCHECKING", ddot_id)

    rows = conn.execute(
        """
        SELECT
            id,
            external_stop_id,
            stop_name,
            latitude,
            longitude
        FROM bus_stops
        WHERE external_stop_id LIKE ?
        """,
        (
            f"%{ddot_id[-5:]}%",
        )
    ).fetchall()


    for r in rows:
        print(dict(r))


conn.close()
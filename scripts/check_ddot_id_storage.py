import sqlite3


DB = "src/database/dmv_bus_stops.db"


ids = [
    "1001352",
    "1001399",
    "1000694",
    "1001294",
    "1002483",
]


conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row


for x in ids:

    print("\nCHECK:", x)

    rows = conn.execute(
        """
        SELECT
            id,
            '[' || external_stop_id || ']' AS stored_id,
            LENGTH(external_stop_id) AS length,
            stop_name
        FROM bus_stops
        WHERE external_stop_id LIKE ?
        """,
        (
            "%" + x[-6:] + "%",
        )
    ).fetchall()


    if not rows:
        print("NONE")

    for r in rows:
        print(dict(r))


conn.close()
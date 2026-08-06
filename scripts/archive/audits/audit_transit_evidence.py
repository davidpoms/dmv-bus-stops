import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

for table in [
    "stop_transit_evidence",
    "stop_observations",
    "stop_consensus"
]:
    print("\n===", table, "===")

    try:
        count = cur.execute(
            f"SELECT COUNT(*) FROM {table}"
        ).fetchone()[0]

        print("count:", count)

        for row in cur.execute(
            f"SELECT * FROM {table} LIMIT 5"
        ):
            print(dict(row))

    except Exception as e:
        print("ERROR:", e)
import sqlite3

conn = sqlite3.connect("src/database/dmv_bus_stops.db")
cur = conn.cursor()

for table in ["physical_stops", "stop_jurisdiction"]:
    print("\n", table)

    cur.execute(f"""
        SELECT state, COUNT(*)
        FROM {table}
        GROUP BY state
    """)

    for row in cur.fetchall():
        print(row)

conn.close()
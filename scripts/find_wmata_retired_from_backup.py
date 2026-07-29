import sqlite3


CURRENT = "src/database/dmv_bus_stops.db"
BACKUPS = [
    "src/database/dmv_bus_stops_before_review_reset.db",
    "src/database/dmv_bus_stops_pre_cleanup.db"
]


current = sqlite3.connect(CURRENT)

current_ids = set(
    r[0]
    for r in current.execute("""
        SELECT DISTINCT wmata_stop_id
        FROM stop_wmata_evidence
        WHERE wmata_stop_id IS NOT NULL
    """)
)


print("Current WMATA IDs:", len(current_ids))


for backup in BACKUPS:

    print("\nChecking:", backup)

    conn = sqlite3.connect(backup)

    old_rows = conn.execute("""
        SELECT
            wmata_stop_id,
            wmata_status,
            wmata_bench,
            wmata_shelter,
            wmata_accessible,
            physical_stop_id
        FROM stop_wmata_evidence
        WHERE wmata_stop_id IS NOT NULL
    """).fetchall()


    retired = [
        r for r in old_rows
        if r[0] not in current_ids
    ]


    print("Old WMATA records:", len(old_rows))
    print("Missing from current:", len(retired))


    for r in retired[:25]:
        print(r)


    conn.close()


current.close()

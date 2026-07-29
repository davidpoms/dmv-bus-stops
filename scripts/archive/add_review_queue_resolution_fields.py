import sqlite3
from pathlib import Path


DB = Path(
    "src/database/dmv_bus_stops.db"
)


conn = sqlite3.connect(DB)
cur = conn.cursor()


columns = [
    (
        "consensus_status",
        "TEXT DEFAULT 'pending'"
    ),
    (
        "resolution_reason",
        "TEXT"
    )
]


for name, definition in columns:

    try:

        cur.execute(
            f"""
            ALTER TABLE review_queue
            ADD COLUMN {name} {definition}
            """
        )

        print(
            "Added:",
            name
        )

    except sqlite3.OperationalError:

        print(
            "Exists:",
            name
        )


conn.commit()
conn.close()


print(
    "✓ Added queue resolution fields"
)

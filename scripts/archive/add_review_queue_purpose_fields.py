import sqlite3
from pathlib import Path


DB = Path(
    "src/database/dmv_bus_stops.db"
)


conn = sqlite3.connect(DB)
cur = conn.cursor()


columns = [
    (
        "verification_needed",
        "INTEGER DEFAULT 1"
    ),
    (
        "community_review_available",
        "INTEGER DEFAULT 1"
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
            "Already exists:",
            name
        )


conn.commit()
conn.close()

print(
    "✓ Added review queue purpose fields"
)

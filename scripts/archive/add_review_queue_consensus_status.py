import sqlite3
from pathlib import Path


DB = Path(
    "src/database/dmv_bus_stops.db"
)


conn = sqlite3.connect(DB)
cur = conn.cursor()


columns = cur.execute(
    """
    PRAGMA table_info(review_queue)
    """
).fetchall()


names = [
    c[1]
    for c in columns
]


if "consensus_status" not in names:

    cur.execute(
        """
        ALTER TABLE review_queue
        ADD COLUMN consensus_status TEXT
        DEFAULT 'pending'
        """
    )

    print(
        "✓ Added consensus_status"
    )

else:

    print(
        "consensus_status already exists"
    )


conn.commit()
conn.close()

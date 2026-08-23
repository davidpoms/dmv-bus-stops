import sqlite3
from pathlib import Path


DB = Path("src/database/dmv_bus_stops.db")


def percentile_rank(values, value):
    below = sum(v < value for v in values)
    return below / len(values) * 100


def generate_priority_levels(db_path=DB):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # This table is a rebuilt active-population output. Remove rows that
    # became non-current (and rows without canonical status) before ranking.
    cursor.execute(
        """
        DELETE FROM stop_improvement_impact
        WHERE NOT EXISTS (
            SELECT 1
            FROM stop_gtfs_status sgs
            WHERE sgs.physical_stop_id =
                  stop_improvement_impact.physical_stop_id
              AND sgs.current_gtfs = 1
        );
        """
    )

    # Add column if needed
    cursor.execute(
    """
    PRAGMA table_info(stop_improvement_impact);
    """
)

    columns = [row[1] for row in cursor.fetchall()]

    if "priority_level" not in columns:
        cursor.execute(
        """
        ALTER TABLE stop_improvement_impact
        ADD COLUMN priority_level TEXT;
        """
    )


    cursor.execute(
    """
    SELECT
        sii.physical_stop_id,
        sii.opportunity_score
    FROM stop_improvement_impact sii
    JOIN stop_gtfs_status sgs
      ON sgs.physical_stop_id = sii.physical_stop_id
     AND sgs.current_gtfs = 1
    ORDER BY sii.opportunity_score;
    """
)

    rows = cursor.fetchall()


    scores = [row[1] for row in rows]


    updated = 0


    for stop_id, score in rows:

        pct = percentile_rank(scores, score)


        if pct >= 99:
            priority = "P1"

        elif pct >= 90:
            priority = "P2"

        elif pct >= 65:
            priority = "P3"

        else:
            priority = "monitor"


        cursor.execute(
        """
        UPDATE stop_improvement_impact

        SET priority_level = ?

        WHERE physical_stop_id = ?;
        """,
        (
            priority,
            stop_id
        )
    )

        updated += 1


    conn.commit()


    cursor.execute(
    """
    SELECT
        priority_level,
        COUNT(*)
    FROM stop_improvement_impact
    GROUP BY priority_level
    ORDER BY priority_level;
    """
)


    print("Priority distribution:")

    for row in cursor.fetchall():
        print(row)


    print(f"Updated {updated} stops")


    conn.close()


if __name__ == "__main__":
    generate_priority_levels()

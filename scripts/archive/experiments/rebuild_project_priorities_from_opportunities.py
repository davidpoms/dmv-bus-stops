import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]

DATABASE_PATH = (
    BASE_DIR
    / "src"
    / "database"
    / "dmv_bus_stops.db"
)


def rebuild():

    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()


    cursor.execute("""
        DELETE FROM project_priorities;
    """)


    cursor.execute("""
        SELECT
            io.physical_stop_id,
            io.opportunity_score,
            io.priority_rank,
            sii.priority_level,
            ps.primary_name
        FROM improvement_opportunities io

        LEFT JOIN stop_improvement_impact sii
            ON io.physical_stop_id = sii.physical_stop_id

        LEFT JOIN physical_stops ps
            ON io.physical_stop_id = ps.id

        WHERE io.opportunity_score >= 70

        ORDER BY io.opportunity_score DESC;
    """)


    rows = cursor.fetchall()


    created = 0


    for row in rows:

        (
            stop_id,
            score,
            rank,
            priority_level,
            location
        ) = row


        priority_level = (
            priority_level
            if priority_level
            else "high"
        )


        cursor.execute("""
            INSERT INTO project_priorities
            (
                physical_stop_id,
                recommendation_type,
                location_name,
                opportunity_score,
                priority_level,
                priority_rank,
                justification
            )

            VALUES (?, ?, ?, ?, ?, ?, ?);
        """,
        (
            stop_id,
            "improvement_opportunity",
            location,
            score,
            priority_level,
            rank,
            (
                f"High opportunity score "
                f"({score:.2f}) based on rider exposure "
                f"and stop conditions"
            )
        ))

        created += 1


    conn.commit()
    conn.close()


    print(
        f"Created {created} project priorities"
    )


if __name__ == "__main__":
    rebuild()

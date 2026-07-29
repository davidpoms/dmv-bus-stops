from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

addition = r'''

def refresh_stop_consensus(stop_id):

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    reviewers = cur.execute(
        """
        SELECT COUNT(
            DISTINCT COALESCE(
                reviewer_id,
                CAST(user_id AS TEXT),
                anonymous_email
            )
        )
        FROM stop_reviews
        WHERE stop_id = ?
        """,
        (stop_id,)
    ).fetchone()[0]


    if reviewers < 3:
        conn.close()
        return False


    review = cur.execute(
        """
        SELECT
            ROUND(AVG(has_shelter),0),
            ROUND(AVG(has_bench),0),
            ROUND(AVG(bench_location_feasible),0),
            ROUND(AVG(
                (
                    curb_access_clear +
                    bus_ramp_access_clear +
                    landing_zone_clear +
                    rear_clear_zone_clear
                ) / 4.0
            ),2),
            AVG(reviewer_confidence)

        FROM stop_reviews
        WHERE stop_id = ?
        """,
        (stop_id,)
    ).fetchone()


    cur.execute(
        """
        INSERT INTO stop_consensus
        (
            stop_id,
            reviewer_count,
            has_shelter,
            has_bench,
            bench_feasible,
            ada_accessible,
            confidence,
            consensus_status
        )

        VALUES (?,?,?,?,?,?,?,'verified')

        ON CONFLICT(stop_id)
        DO UPDATE SET

            reviewer_count=excluded.reviewer_count,
            has_shelter=excluded.has_shelter,
            has_bench=excluded.has_bench,
            bench_feasible=excluded.bench_feasible,
            ada_accessible=excluded.ada_accessible,
            confidence=excluded.confidence,
            consensus_status='verified'
        """,
        (
            stop_id,
            reviewers,
            review[0],
            review[1],
            review[2],
            review[3],
            review[4],
        )
    )


    cur.execute(
        """
        UPDATE stop_validation
        SET
            status='validated',
            validated_at=CURRENT_TIMESTAMP
        WHERE physical_stop_id=?
        """,
        (stop_id,)
    )


    conn.commit()
    conn.close()

    return True

'''

if "def refresh_stop_consensus" not in text:
    text += addition

p.write_text(text)

print("Added consensus refresh function")

import sqlite3

DB = "src/database/dmv_bus_stops.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()


cur.execute("""
DELETE FROM stop_consensus;
""")


stops = cur.execute("""
SELECT
    sr.stop_id

FROM stop_reviews sr

JOIN stop_review_assignments a
ON a.stop_id = sr.stop_id

WHERE a.status='completed'

GROUP BY sr.stop_id

HAVING COUNT(
    DISTINCT a.reviewer_id
) >= 3

""").fetchall()


created = 0


for (stop_id,) in stops:

    rows = cur.execute("""
        SELECT

            has_bench,
            bench_location_feasible,
            concrete_pad_present,
            reviewer_confidence

        FROM stop_reviews

        WHERE stop_id=?

    """, (stop_id,)).fetchall()


    count = len(rows)


    bench_yes = sum(
        1 for r in rows
        if r[0] in (1, "1", True, "true")
    )


    feasible_yes = sum(
        1 for r in rows
        if r[1] in (1, "1", True, "true")
    )


    pad_yes = sum(
        1 for r in rows
        if r[2] in (1, "1", True, "true")
    )


    confidence = sum(
        (r[3] or 0)
        for r in rows
    ) / count


    cur.execute("""
    INSERT INTO stop_consensus
    (
        stop_id,
        reviewer_count,
        has_bench,
        bench_feasible,
        ada_accessible,
        confidence,
        consensus_status
    )

    VALUES
    (?, ?, ?, ?, ?, ?, 'verified')

    """,
    (
        stop_id,
        count,
        bench_yes >= (count / 2),
        feasible_yes >= (count / 2),
        pad_yes >= (count / 2),
        confidence
    ))

    created += 1


conn.commit()
conn.close()


print(
    f"Consensus records created: {created}"
)

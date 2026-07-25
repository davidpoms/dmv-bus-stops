import sqlite3

DB = "src/database/dmv_bus_stops.db"


conn = sqlite3.connect(DB)
cur = conn.cursor()


stops = cur.execute("""
SELECT
    stop_id
FROM stop_reviews
GROUP BY stop_id
HAVING COUNT(
    DISTINCT COALESCE(
        reviewer_id,
        CAST(user_id AS TEXT),
        anonymous_email
    )
) >= 3
""").fetchall()


updated = 0


for (stop_id,) in stops:

    reviews = cur.execute(
        """
        SELECT
            has_shelter,
            has_bench,
            bench_location_feasible,
            curb_access_clear,
            bus_ramp_access_clear,
            landing_zone_clear,
            rear_clear_zone_clear
        FROM stop_reviews
        WHERE stop_id = ?
        """,
        (stop_id,)
    ).fetchall()


    def majority(index):

        values = [
            r[index]
            for r in reviews
            if r[index] is not None
        ]

        if not values:
            return None, 0

        yes_count = sum(
            1 for x in values if x == 1
        )

        no_count = sum(
            1 for x in values if x == 0
        )

        total = yes_count + no_count

        if total == 0:
            return None, 0

        confidence = max(
            yes_count,
            no_count
        ) / total

        return (
            1 if yes_count > no_count else 0,
            confidence
        )


    shelter, shelter_conf = majority(0)
    bench, bench_conf = majority(1)
    feasible, feasible_conf = majority(2)

    curb, curb_conf = majority(3)
    ramp, ramp_conf = majority(4)
    landing, landing_conf = majority(5)
    rear, rear_conf = majority(6)


    confidence_values = [
        x for x in [
            shelter_conf,
            bench_conf,
            feasible_conf,
            curb_conf,
            ramp_conf,
            landing_conf,
            rear_conf,
        ]
        if x
    ]


    confidence = (
        sum(confidence_values) /
        len(confidence_values)
        if confidence_values
        else 0
    )


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
        VALUES (?,?,?,?,?,?,?,?)
        ON CONFLICT(stop_id)
        DO UPDATE SET

            reviewer_count=excluded.reviewer_count,
            has_shelter=excluded.has_shelter,
            has_bench=excluded.has_bench,
            bench_feasible=excluded.bench_feasible,
            ada_accessible=excluded.ada_accessible,
            confidence=excluded.confidence,
            consensus_status='verified',
            updated_at=CURRENT_TIMESTAMP
        """,
        (
            stop_id,
            len(reviews),
            shelter,
            bench,
            feasible,
            (
                1
                if (
                    curb == 1
                    and ramp == 1
                    and landing == 1
                    and rear == 1
                )
                else 0
            ),
            confidence,
            "verified",
        )
    )

    updated += 1


conn.commit()

print(
    f"Consensus records updated: {updated}"
)

conn.close()

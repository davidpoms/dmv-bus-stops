import sqlite3

DB = "src/database/dmv_bus_stops.db"

MIN_REVIEWS = 4
AGREEMENT_THRESHOLD = 0.75


def pct(value, total):
    return value / total if total else 0


conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

cur = conn.cursor()


# clear old consensus
cur.execute(
    "DELETE FROM stop_consensus"
)


stops = cur.execute(
    """
    SELECT DISTINCT physical_stop_id
    FROM stop_observations
    """
).fetchall()


for row in stops:

    stop_id = row["physical_stop_id"]


    reviews = cur.execute(
        """
        SELECT *
        FROM stop_observations
        WHERE physical_stop_id=?
        """,
        (stop_id,)
    ).fetchall()


    reviewers = {
        r["reviewer_id"]
        for r in reviews
        if r["reviewer_id"] is not None
    }


    count = len(reviewers)


    if count < MIN_REVIEWS:
        continue


    def agreement(field):

        values = {}

        for r in reviews:
            reviewer = r["reviewer_id"]

            if reviewer not in values:
                values[reviewer] = r[field]


        yes = sum(
            1
            for v in values.values()
            if v == "yes"
        )

        return pct(yes, len(values))


    bench_pct = agreement(
        "bench_present"
    )

    shelter_pct = agreement(
        "shelter_present"
    )

    feasible_pct = agreement(
        "bench_feasible"
    )

    ada_pct = agreement(
        "ada_clearance_possible"
    )


    confidence = max(
        bench_pct,
        shelter_pct,
        feasible_pct,
        ada_pct
    )


    cur.execute(
        """
        INSERT INTO stop_consensus
        (
            stop_id,
            reviewer_count,
            has_bench,
            has_shelter,
            bench_feasible,
            ada_accessible,
            confidence,
            consensus_status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            stop_id,
            count,
            bench_pct >= AGREEMENT_THRESHOLD,
            shelter_pct >= AGREEMENT_THRESHOLD,
            feasible_pct >= AGREEMENT_THRESHOLD,
            ada_pct >= AGREEMENT_THRESHOLD,
            confidence,
            "verified"
        )
    )


conn.commit()
conn.close()

print("Consensus rebuilt")

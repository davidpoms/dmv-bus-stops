from pathlib import Path


path = Path(
    "src/review/assignment_router.py"
)

text = path.read_text()


start = text.index(
    "def assign_stop("
)


new_function = r"""
def assign_stop(
    reviewer_id,
    scenario
):

    conn = sqlite3.connect(DB)
    cur = conn.cursor()


    existing = cur.execute(
        '''
        SELECT
            id,
            stop_id

        FROM stop_review_assignments

        WHERE reviewer_id=?
        AND scenario=?
        AND status='assigned'

        ORDER BY id DESC

        LIMIT 1
        ''',
        (
            reviewer_id,
            scenario
        )
    ).fetchone()


    if existing:

        conn.close()

        return existing[0], existing[1]


    if scenario == "opportunity":

        stop = cur.execute(
            """
            SELECT physical_stop_id

            FROM review_queue

            WHERE verification_needed=1

            ORDER BY priority_rank

            LIMIT 1
            """
        ).fetchone()


    elif scenario == "nearby":

        stop = cur.execute(
            """
            SELECT physical_stop_id

            FROM review_queue

            WHERE community_review_available=1

            ORDER BY RANDOM()

            LIMIT 1
            """
        ).fetchone()


    elif scenario == "route":

        stop = cur.execute(
            """
            SELECT physical_stop_id

            FROM review_queue

            WHERE community_review_available=1

            ORDER BY RANDOM()

            LIMIT 1
            """
        ).fetchone()


    else:

        raise ValueError(
            "Unknown scenario"
        )


    if not stop:

        conn.close()

        return None


    stop_id = stop[0]


    cur.execute(
        """
        INSERT INTO stop_review_assignments
        (
            stop_id,
            reviewer_id,
            scenario
        )

        VALUES (?, ?, ?)
        """,
        (
            stop_id,
            reviewer_id,
            scenario
        )
    )


    assignment = cur.execute(
        """
        SELECT id

        FROM stop_review_assignments

        WHERE stop_id=?
        AND reviewer_id=?

        ORDER BY id DESC

        LIMIT 1
        """,
        (
            stop_id,
            reviewer_id
        )
    ).fetchone()


    conn.commit()
    conn.close()


    return assignment[0], stop_id
"""


text = text[:start] + new_function


path.write_text(text)


print(
    "✓ Rewrote assignment router routing logic"
)

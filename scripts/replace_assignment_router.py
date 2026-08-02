from pathlib import Path

path = Path("src/review/assignment_router.py")

text = path.read_text()

start = text.find("def assign_stop(")

if start == -1:
    raise Exception("Could not find assign_stop function")

new_function = r'''
def assign_stop(
    reviewer_id,
    scenario,
    stop_id=None,
    latitude=None,
    longitude=None
):

    conn = sqlite3.connect(DB)
    cur = conn.cursor()


    if stop_id:

        if not stop_is_active(stop_id):
            conn.close()
            return None

        row = cur.execute(
            """
            SELECT
                id,
                physical_stop_id
            FROM review_queue
            WHERE physical_stop_id=?
            LIMIT 1
            """,
            (stop_id,)
        ).fetchone()


    elif scenario == "nearby" and latitude and longitude:

        row = cur.execute(
            """
            SELECT
                rq.id,
                rq.physical_stop_id
            FROM review_queue rq
            JOIN physical_stops ps
                ON ps.id = rq.physical_stop_id
            WHERE rq.community_review_available=1
            AND rq.review_status='pending'
            ORDER BY
                (
                    (ps.latitude - ?) *
                    (ps.latitude - ?)
                    +
                    (ps.longitude - ?) *
                    (ps.longitude - ?)
                )
            LIMIT 1
            """,
            (
                latitude,
                latitude,
                longitude,
                longitude
            )
        ).fetchone()


    else:

        row = cur.execute(
            """
            SELECT
                id,
                physical_stop_id
            FROM review_queue
            WHERE review_status='pending'
            AND community_review_available=1
            ORDER BY priority_rank
            LIMIT 1
            """
        ).fetchone()


    if not row:
        conn.close()
        return None


    stop_id = row[1]


    cur.execute(
        """
        INSERT INTO stop_review_assignments
        (
            stop_id,
            reviewer_id,
            scenario,
            status
        )
        VALUES (?, ?, ?, 'assigned')
        """,
        (
            stop_id,
            reviewer_id,
            scenario
        )
    )


    assignment_id = cur.lastrowid

    conn.commit()
    conn.close()


    return assignment_id, stop_id
'''

text = text[:start] + new_function + "\n"

path.write_text(text)

print("Replaced assign_stop()")
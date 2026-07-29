from pathlib import Path

p = Path("src/review/assignment_router.py")

text = p.read_text()


needle = """
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

"""

replacement = """
    conn = sqlite3.connect(DB)
    cur = conn.cursor()


    def stop_is_active(stop_id):

        row = cur.execute(
            \"\"\"
            SELECT
                w.wmata_status
            FROM physical_stops p
            LEFT JOIN stop_wmata_evidence w
                ON p.id = w.physical_stop_id
            WHERE p.id=?
            \"\"\",
            (stop_id,)
        ).fetchone()


        if not row:
            return True


        status = row[0]

        return status != "ABS"


"""

if needle not in text:
    raise Exception("Could not find DB connection block")

text = text.replace(
    needle,
    replacement,
    1
)


# Manual stop_id validation

old = """
    if stop_id:

        stop = (
            stop_id,
        )

"""

new = """
    if stop_id:

        if not stop_is_active(stop_id):
            conn.close()
            return None

        stop = (
            stop_id,
        )

"""

if old not in text:
    raise Exception("Could not find stop_id block")

text = text.replace(
    old,
    new,
    1
)


# opportunity queue filter

old = """
            SELECT physical_stop_id
            FROM review_queue
            WHERE verification_needed=1
            ORDER BY priority_rank
            LIMIT 1
"""

new = """
            SELECT rq.physical_stop_id
            FROM review_queue rq
            LEFT JOIN stop_wmata_evidence w
                ON rq.physical_stop_id = w.physical_stop_id
            WHERE rq.verification_needed=1
            AND (
                w.wmata_status IS NULL
                OR w.wmata_status != 'ABS'
            )
            ORDER BY rq.priority_rank
            LIMIT 1
"""

if old not in text:
    raise Exception("Could not find opportunity query")

text = text.replace(
    old,
    new,
    1
)


# route query

old = """
            SELECT physical_stop_id
            FROM review_queue
            WHERE community_review_available=1
            ORDER BY priority_rank
            LIMIT 1
"""

new = """
            SELECT rq.physical_stop_id
            FROM review_queue rq
            LEFT JOIN stop_wmata_evidence w
                ON rq.physical_stop_id = w.physical_stop_id
            WHERE rq.community_review_available=1
            AND (
                w.wmata_status IS NULL
                OR w.wmata_status != 'ABS'
            )
            ORDER BY rq.priority_rank
            LIMIT 1
"""

text = text.replace(
    old,
    new,
    1
)


p.write_text(text)

print("Filtered inactive WMATA ABS stops from review assignments")

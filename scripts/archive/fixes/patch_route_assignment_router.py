from pathlib import Path


path = Path("src/review/assignment_router.py")

text = path.read_text(encoding="utf-8")


old = """
    elif scenario == "route":

        row = cur.execute(
            \"\"\"
            SELECT
                rq.id,
                rq.physical_stop_id

            FROM review_queue rq

            JOIN stop_routes sr

                ON sr.stop_id = rq.physical_stop_id


            WHERE rq.review_status='pending'

            AND rq.community_review_available=1


            AND rq.physical_stop_id NOT IN (

                SELECT stop_id

                FROM stop_review_assignments

                WHERE reviewer_id=?

            )


            AND rq.physical_stop_id NOT IN (

                SELECT stop_id

                FROM stop_review_assignments

                WHERE status='assigned'

            )


            GROUP BY rq.physical_stop_id

            ORDER BY rq.priority_rank

            LIMIT 1
            \"\"\",
            (
                reviewer_id,
            )
        ).fetchone()
"""


new = """
    elif scenario == "route":

        row = cur.execute(
            \"\"\"
            SELECT
                rq.id,
                rq.physical_stop_id

            FROM review_queue rq

            JOIN stop_routes sr
                ON sr.stop_id = rq.physical_stop_id

            JOIN community_reviewer_routes crr
                ON crr.route_id = sr.route_id

            WHERE crr.reviewer_id = ?

            AND rq.review_status='pending'

            AND rq.community_review_available=1

            AND rq.physical_stop_id NOT IN (

                SELECT stop_id

                FROM stop_review_assignments

                WHERE reviewer_id=?

            )

            AND rq.physical_stop_id NOT IN (

                SELECT stop_id

                FROM stop_review_assignments

                WHERE status='assigned'

            )

            GROUP BY rq.physical_stop_id

            ORDER BY rq.priority_rank

            LIMIT 1

            \"\"\",
            (
                reviewer_id,
                reviewer_id
            )
        ).fetchone()
"""


if old not in text:
    raise SystemExit(
        "Could not find route assignment block. No changes made."
    )


backup = path.with_suffix(".py.route_backup")

backup.write_text(text, encoding="utf-8")

updated = text.replace(old, new)

path.write_text(updated, encoding="utf-8")


print("Updated:", path)
print("Backup created:", backup)
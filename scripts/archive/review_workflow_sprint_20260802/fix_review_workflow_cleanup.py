from pathlib import Path


APP = Path("src/api/app.py")


text = APP.read_text(encoding="utf-8")


# --------------------------------------------------
# Remove duplicate assignment query block
# --------------------------------------------------

duplicate_block = """
        assignment = query_db(
            \"\"\"
            SELECT
                id,
                reviewer_id,
                stop_id

            FROM stop_review_assignments

            WHERE stop_id=?

            AND status='assigned'

            ORDER BY id DESC

            LIMIT 1
            \"\"\",
            (
                stop_id,
            )
        )



        assignment = query_db(
            \"\"\"
            SELECT
                id,
                reviewer_id,
                stop_id

            FROM stop_review_assignments

            WHERE stop_id=?

            AND status='assigned'

            ORDER BY id DESC

            LIMIT 1
            \"\"\",
            (
                stop_id,
            )
        )
"""


replacement = """
        assignment = query_db(
            \"\"\"
            SELECT
                id,
                reviewer_id,
                stop_id

            FROM stop_review_assignments

            WHERE stop_id=?

            AND status='assigned'

            ORDER BY id DESC

            LIMIT 1
            \"\"\",
            (
                stop_id,
            )
        )
"""


if duplicate_block in text:
    text = text.replace(
        duplicate_block,
        replacement
    )
    print("Removed duplicate assignment query")
else:
    print("Duplicate assignment block not found")


# --------------------------------------------------
# Add duplicate submit protection
# --------------------------------------------------

needle = """
    if not assignment_id or not reviewer_id:
        return {
            "error": "assignment_id and reviewer_id required"
        }, 400
"""


insert = """
    if not assignment_id or not reviewer_id:
        return {
            "error": "assignment_id and reviewer_id required"
        }, 400


    existing_review = query_db(
        \"\"\"
        SELECT id
        FROM stop_observations
        WHERE physical_stop_id=?
        AND reviewer_id=?
        AND source='community_review'
        LIMIT 1
        \"\"\",
        (
            stop_id,
            reviewer_id
        )
    )


    if existing_review:
        return {
            "success": True,
            "message": "Review already submitted",
            "stop_id": stop_id,
            "reviewer_id": reviewer_id
        }
"""


if needle in text:
    text = text.replace(
        needle,
        insert
    )
    print("Added duplicate review protection")
else:
    print("Submit validation block not found")


# --------------------------------------------------
# Remove unused ridership_exposure query
# --------------------------------------------------

start = text.find("""
    ridership_exposure = query_db(
""")

if start != -1:
    end = text.find("""
    first_review = (
""", start)

    if end != -1:
        text = text[:start] + text[end:]
        print("Removed unused ridership query")
else:
    print("Ridership query not found")


APP.write_text(
    text,
    encoding="utf-8"
)

print("Review workflow cleanup complete")
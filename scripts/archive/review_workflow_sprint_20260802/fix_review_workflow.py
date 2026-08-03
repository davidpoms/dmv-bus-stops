from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()


# -------------------------------------------------
# 1. Remove duplicated assignment query
# -------------------------------------------------

duplicate = """
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
"""

replacement = """
        assignment = query_db(
"""

if duplicate in text:
    text = text.replace(
        duplicate,
        replacement,
        1
    )
    print("Removed duplicate assignment lookup")
else:
    print("Duplicate assignment block not found")


# -------------------------------------------------
# 2. Add ridership_exposure lookup before response
# -------------------------------------------------

needle = """
    first_review = (
"""

insert = """
    ridership_exposure = query_db(
        \"\"\"
        SELECT
            average_weekday_boardings,
            route_count,
            routes

        FROM stop_ridership_exposure

        WHERE stop_id=?

        LIMIT 1
        \"\"\",
        (
            stop_id,
        )
    )



"""

if needle in text:
    text = text.replace(
        needle,
        insert + needle,
        1
    )
    print("Added ridership lookup")
else:
    print("Could not find first_review section")


# -------------------------------------------------
# 3. Make ridership handling safe
# -------------------------------------------------

old = """
        "community_impact": {
            "daily_route_exposure":
                impact[0][0]
                if impact
                else None,
"""

new = """
        "community_impact": {
            "daily_route_exposure":
                ridership_exposure[0][0]
                if ridership_exposure
                else None,
"""

if old in text:
    text = text.replace(
        old,
        new,
        1
    )
    print("Fixed community impact reference")
else:
    print("Community impact block already changed")


path.write_text(text)

print("Review workflow patch complete")
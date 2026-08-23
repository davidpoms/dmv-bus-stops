from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()


old_block = """
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

new_block = """
    ridership_exposure = query_db(
        \"\"\"
        SELECT
            SUM(rs.weekday_boardings) AS weekday_boardings,
            COUNT(DISTINCT r.route_id) AS route_count,
            GROUP_CONCAT(DISTINCT r.route_id)

        FROM stop_routes sr

        JOIN routes r
            ON r.id = sr.route_id

        JOIN ridership_snapshots rs
            ON rs.route_id = r.route_id

        WHERE sr.stop_id = ?

        \"\"\",
        (
            stop_id,
        )
    )


"""


if old_block in text:
    text = text.replace(
        old_block,
        new_block,
        1
    )
    print("Replaced ridership lookup")
else:
    print("Old ridership block not found")


path.write_text(text)

print("Ridership impact patch complete")
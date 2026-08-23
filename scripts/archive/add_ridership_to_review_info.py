from pathlib import Path
import shutil
from datetime import datetime


path = Path("src/api/app.py")

backup = path.with_name(
    f"app_before_review_info_ridership_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
)

shutil.copy(path, backup)

print("Backup:", backup)


text = path.read_text()


target = """
    streetview = get_road_index().nearest_road(
        row[2],
        row[3]
    )
"""


insert = """

    ridership = query_db(
        '''
        SELECT
            SUM(rs.weekday_boardings) AS weekday_total,
            COUNT(DISTINCT r.route_id) AS route_count,
            GROUP_CONCAT(DISTINCT r.route_id) AS routes

        FROM stop_routes sr

        JOIN routes r
            ON sr.route_id = r.route_id

        JOIN ridership_snapshots rs
            ON r.route_id = rs.route_id

        WHERE sr.stop_id = ?

        AND rs.period = (
            SELECT MAX(period)
            FROM ridership_snapshots
        )

        GROUP BY sr.stop_id
        ''',
        (stop_id,)
    )


    ridership_exposure = (
        {
            "weekday_boardings_total":
                round(ridership[0][0])
                if ridership[0][0]
                else 0,

            "average_weekday_boardings":
                round(ridership[0][0] / 23)
                if ridership[0][0]
                else 0,

            "route_count":
                ridership[0][1]
                or 0,

            "routes":
                ridership[0][2].split(",")
                if ridership[0][2]
                else []
        }
        if ridership
        else None
    )

"""


if insert.strip() not in text:

    if target not in text:
        raise Exception("Could not find insertion point")

    text = text.replace(
        target,
        insert + target
    )


return_target = """
            "streetview_url": streetview_url,
"""

return_insert = """
            "ridership_exposure":
                ridership_exposure,

"""

if return_insert.strip() not in text:

    if return_target not in text:
        raise Exception("Could not find JSON return point")

    text = text.replace(
        return_target,
        return_insert + return_target,
        1
    )


path.write_text(text)

print("Added ridership to review info endpoint")
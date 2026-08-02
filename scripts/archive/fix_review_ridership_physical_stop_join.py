from pathlib import Path
import shutil
from datetime import datetime


path = Path("src/api/app.py")

backup = path.with_name(
    f"app_before_review_ridership_join_final_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
)

shutil.copy(path, backup)

print("Backup:", backup)


text = path.read_text()


old = """
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
"""


new = """
    ridership = query_db(
        '''
        SELECT
            SUM(rs.weekday_boardings) AS weekday_total,
            COUNT(DISTINCT r.route_id) AS route_count,
            GROUP_CONCAT(DISTINCT r.route_id) AS routes

        FROM physical_stop_members psm

        JOIN stop_routes sr
            ON psm.bus_stop_id = sr.stop_id

        JOIN routes r
            ON sr.route_id = r.id

        JOIN ridership_snapshots rs
            ON r.route_id = rs.route_id

        WHERE psm.physical_stop_id = ?

        AND rs.period = (
            SELECT MAX(period)
            FROM ridership_snapshots
        )

        GROUP BY psm.physical_stop_id
        ''',
        (stop_id,)
    )
"""


if old not in text:
    raise Exception(
        "Could not find old ridership query"
    )


text = text.replace(old,new)


path.write_text(text)

print("Updated review ridership join.")
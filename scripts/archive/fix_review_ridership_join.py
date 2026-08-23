from pathlib import Path
import re
from datetime import datetime
import shutil


APP = Path("src/api/app.py")

backup = APP.with_name(
    f"app_before_review_ridership_join_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
)

shutil.copy(APP, backup)

print("Backup:", backup)


text = APP.read_text(encoding="utf-8")


old = re.compile(
r"""
    ridership = query_db\(
        '''
        SELECT
            SUM\(rs\.weekday_boardings\).*?
        GROUP BY sr\.stop_id
        ''',
        \(stop_id,\)
    \)
""",
re.S
)


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


updated, count = old.subn(new, text)


if count == 0:
    raise Exception(
        "Could not find old ridership query block"
    )


APP.write_text(updated, encoding="utf-8")

print("Updated review ridership join.")
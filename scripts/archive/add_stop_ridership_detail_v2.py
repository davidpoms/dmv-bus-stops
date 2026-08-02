from pathlib import Path
import shutil
from datetime import datetime

path = Path("src/api/app.py")

backup = Path(
    f"src/api/app_before_ridership_detail_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
)

shutil.copy(path, backup)

print("Backup:", backup)


text = path.read_text()


old = """
GROUP_CONCAT(DISTINCT r.route_name) AS routes
"""


new = """
GROUP_CONCAT(DISTINCT r.route_name) AS routes,

GROUP_CONCAT(
    DISTINCT sr.route_id
) AS route_ids,

COALESCE(
    SUM(
        rs.weekday_boardings
    ),
    0
) AS weekday_boardings

"""


if old not in text:
    raise Exception(
        "Could not find route aggregation block"
    )


text = text.replace(
    old,
    new,
    1
)


old_join = """
LEFT JOIN routes r
    ON sr.route_id = r.route_id
"""


new_join = """
LEFT JOIN routes r
    ON sr.route_id = r.route_id

LEFT JOIN ridership_snapshots rs
    ON sr.route_id = rs.route_id

"""


if old_join not in text:
    raise Exception(
        "Could not find route join"
    )


text = text.replace(
    old_join,
    new_join,
    1
)


old_json = """
"routes": stop_row[5].split(",") if stop_row[5] else []
"""


new_json = """
"routes": stop_row[5].split(",") if stop_row[5] else [],

"route_ids":
    stop_row[6].split(",")
    if stop_row[6]
    else [],

"weekday_boardings":
    stop_row[7] or 0
"""


if old_json not in text:
    raise Exception(
        "Could not find stop JSON block"
    )


text = text.replace(
    old_json,
    new_json,
    1
)


path.write_text(text)

print("Added ridership fields")
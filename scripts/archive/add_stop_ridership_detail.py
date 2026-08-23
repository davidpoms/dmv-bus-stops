from pathlib import Path
import shutil


path = Path("src/api/app.py")

backup = Path(
    "src/api/app_before_ridership_detail_fix.py"
)

shutil.copy(path, backup)

text = path.read_text()


old = """
LEFT JOIN routes r
    ON sr.route_id = r.route_id

WHERE ps.id = ?

GROUP BY ps.id
"""


new = """
LEFT JOIN routes r
    ON sr.route_id = r.route_id

LEFT JOIN ridership_snapshots rs
    ON sr.route_id = rs.route_id

WHERE ps.id = ?

GROUP BY ps.id
"""


if old not in text:
    raise Exception(
        "Could not find route join section"
    )


text = text.replace(old,new)


old_select = """
GROUP_CONCAT(DISTINCT r.route_name) AS routes
"""

new_select = """
GROUP_CONCAT(DISTINCT r.route_name) AS routes,

SUM(
    COALESCE(rs.monthly_boardings,0)
) AS monthly_boardings
"""


if old_select not in text:
    raise Exception(
        "Could not find route select"
    )


text = text.replace(
    old_select,
    new_select,
    1
)


old_json = """
"routes": stop_row[5].split(",") if stop_row[5] else []
"""


new_json = """
"routes": stop_row[5].split(",") if stop_row[5] else [],

"monthly_boardings":
    stop_row[6] if stop_row[6] else 0
"""


if old_json not in text:
    raise Exception(
        "Could not find JSON section"
    )


text = text.replace(
    old_json,
    new_json
)


path.write_text(text)

print("Added ridership to stop detail")
print("Backup:", backup)
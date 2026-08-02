from pathlib import Path
from datetime import datetime
import shutil


path = Path("src/api/app.py")

backup = Path(
    f"src/api/app_backup_before_wmata_map_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
)

shutil.copy(path, backup)

print(f"Backup created: {backup}")


text = path.read_text(encoding="utf-8")


# Only operate inside map_stops()
start = text.index('@app.route("/map/stops")')
end = text.index('@app.route', start + 10)

section = text[start:end]


# Add WMATA ID after every ps.id in the map SELECTs
old = """
                ps.id,
                ps.primary_name,
"""

new = """
                ps.id,
                we.wmata_stop_id,
                ps.primary_name,
"""


count = section.count(old)

if count == 0:
    raise Exception(
        "Could not find map SELECT blocks"
    )

section = section.replace(
    old,
    new
)


# Add WMATA join after every physical_stops FROM
old = """
            FROM physical_stops ps

            LEFT JOIN improvement_opportunities io
"""


new = """
            FROM physical_stops ps

            JOIN stop_wmata_evidence we
                ON ps.id = we.physical_stop_id

            LEFT JOIN improvement_opportunities io
"""


count = section.count(old)

if count == 0:
    raise Exception(
        "Could not find physical_stops joins"
    )

section = section.replace(
    old,
    new
)


text = (
    text[:start]
    + section
    + text[end:]
)


path.write_text(
    text,
    encoding="utf-8"
)


print(
    "Updated map_stops() to filter to WMATA stops and expose WMATA stop IDs"
)
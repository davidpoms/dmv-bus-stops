from pathlib import Path
import shutil
from datetime import datetime


path = Path("src/api/app.py")

backup = Path(
    f"src/api/app_before_stop_detail_ridership_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
)

shutil.copy(path, backup)

print("Backup created:")
print(backup)


text = path.read_text()


# Find the stop_detail function area only
start = text.find("def stop_detail(stop_id):")

if start == -1:
    raise Exception("Could not find stop_detail function")


end = text.find("@app.route", start + 10)

if end == -1:
    end = len(text)


section = text[start:end]


# Prevent duplicate patch
if "ridership_exposure" in section:
    raise Exception(
        "ridership_exposure already exists in stop_detail"
    )


# Insert ridership query before return jsonify
marker = """
    return jsonify(
"""


ridership_code = """
    ridership = query_db(
        """
        SELECT
            SUM(rs.weekday_boardings) AS total_boardings,
            COUNT(DISTINCT r.route_id) AS route_count,
            GROUP_CONCAT(DISTINCT r.route_id) AS routes

        FROM physical_stop_members psm

        JOIN bus_stops bs
            ON psm.bus_stop_id = bs.id

        JOIN stop_routes sr
            ON bs.id = sr.stop_id

        JOIN routes r
            ON sr.route_id = r.route_id

        JOIN ridership_snapshots rs
            ON r.route_id = rs.route_id

        WHERE psm.physical_stop_id = ?

        AND rs.period = (
            SELECT MAX(period)
            FROM ridership_snapshots
        )

        GROUP BY psm.physical_stop_id
        """,
        (stop_id,)
    )


    ridership_exposure = (
        {
            "weekday_boardings":
                round(ridership[0][0])
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


if marker not in section:
    raise Exception(
        "Could not find return jsonify marker"
    )


section = section.replace(
    marker,
    ridership_code + marker,
    1
)


# Add JSON field
old = """
            "wmata_evidence": wmata_evidence
"""

new = """
            "wmata_evidence": wmata_evidence,

            "ridership_exposure":
                ridership_exposure
"""


if old not in section:
    raise Exception(
        "Could not find wmata_evidence JSON field"
    )


section = section.replace(
    old,
    new,
    1
)


text = (
    text[:start]
    + section
    + text[end:]
)


path.write_text(text)

print("Added ridership exposure to stop_detail")
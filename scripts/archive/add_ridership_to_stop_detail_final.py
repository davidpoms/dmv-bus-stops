from pathlib import Path
from datetime import datetime
import shutil


path = Path("src/api/app.py")

text = path.read_text(encoding="utf-8")


backup = path.with_name(
    f"app_before_stop_detail_ridership_{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
)

print("Backup:", backup)

shutil.copy(path, backup)


# Add ridership query before return jsonify inside stop_detail
marker = """
    wmata_history = get_wmata_history(stop_id)

    wmata_evidence = get_wmata_evidence(stop_id)


    return jsonify(
"""


replacement = """
    wmata_history = get_wmata_history(stop_id)

    wmata_evidence = get_wmata_evidence(stop_id)


    ridership = query_db(
        '''
        SELECT
            SUM(rs.weekday_boardings) AS weekday_boardings,
            COUNT(DISTINCT r.route_id) AS route_count,
            GROUP_CONCAT(DISTINCT r.route_id) AS routes

        FROM physical_stop_members psm

        JOIN bus_stops bs
            ON psm.bus_stop_id = bs.id

        JOIN stop_routes sr
            ON bs.id = sr.stop_id

        JOIN routes r
            ON sr.route_id = r.route_id

        LEFT JOIN ridership_snapshots rs
            ON r.route_id = rs.route_id

        WHERE psm.physical_stop_id = ?

        AND (
            rs.period IS NULL
            OR rs.period = (
                SELECT MAX(period)
                FROM ridership_snapshots
            )
        )

        GROUP BY psm.physical_stop_id
        ''',
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
        else {
            "weekday_boardings": 0,
            "route_count": 0,
            "routes": []
        }
    )


    return jsonify(
"""


if marker not in text:
    raise Exception("Could not find stop detail insertion point")


text = text.replace(marker, replacement, 1)


old = """
            "wmata_evidence": wmata_evidence
        }
    )
"""


new = """
            "wmata_evidence": wmata_evidence,

            "ridership_exposure":
                ridership_exposure
        }
    )
"""


if old not in text:
    raise Exception("Could not find JSON return block")


text = text.replace(old, new, 1)


path.write_text(text, encoding="utf-8")

print("Added ridership_exposure to stop detail endpoint")
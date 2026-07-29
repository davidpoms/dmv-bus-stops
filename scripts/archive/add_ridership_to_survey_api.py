from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()


old = """
    wmata_evidence = query_db(
        '''
        SELECT
            wmata_status,
            wmata_bench,
            wmata_shelter,
            wmata_accessible,
            match_confidence,
            match_distance_m
        FROM stop_wmata_evidence
        WHERE physical_stop_id = ?
        ''',
        (stop_id,)
    )


    road = get_road_index().nearest_road(
"""


new = """
    wmata_evidence = query_db(
        '''
        SELECT
            wmata_status,
            wmata_bench,
            wmata_shelter,
            wmata_accessible,
            match_confidence,
            match_distance_m
        FROM stop_wmata_evidence
        WHERE physical_stop_id = ?
        ''',
        (stop_id,)
    )


    ridership = query_db(
        '''
        SELECT
            SUM(rs.weekday_boardings) AS total_boardings,
            COUNT(DISTINCT r.route_id) AS route_count,
            GROUP_CONCAT(DISTINCT r.route_id) AS routes

        FROM stop_routes sr

        JOIN routes r
            ON sr.route_id = r.id

        JOIN ridership_snapshots rs
            ON r.route_id = rs.route_id

        WHERE sr.physical_stop_id = ?

        GROUP BY sr.physical_stop_id
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
        else None
    )


    road = get_road_index().nearest_road(
"""


if old not in text:
    raise Exception("Could not find WMATA query block")


text = text.replace(old, new)


old2 = """
            "wmata_evidence": (
                {
                    "status": wmata_evidence[0][0],
                    "bench": wmata_evidence[0][1],
                    "shelter": wmata_evidence[0][2],
                    "accessible": wmata_evidence[0][3],
                    "confidence": wmata_evidence[0][4],
                    "distance_meters": wmata_evidence[0][5]
                }
                if wmata_evidence
                else None
            )
        }
    )
"""


new2 = """
            "wmata_evidence": (
                {
                    "status": wmata_evidence[0][0],
                    "bench": wmata_evidence[0][1],
                    "shelter": wmata_evidence[0][2],
                    "accessible": wmata_evidence[0][3],
                    "confidence": wmata_evidence[0][4],
                    "distance_meters": wmata_evidence[0][5]
                }
                if wmata_evidence
                else None
            ),

            "ridership_exposure":
                ridership_exposure
        }
    )
"""


if old2 not in text:
    raise Exception("Could not find JSON response block")


text = text.replace(old2, new2)


p.write_text(text)

print("Added ridership exposure to /survey endpoint")

from pathlib import Path
import shutil

path = Path("src/api/app.py")

backup = Path("src/api/app_before_route_map_query_fix.py")
shutil.copy(path, backup)

text = path.read_text()

start = text.index("    if route:")

end = text.index("    else:", start)

replacement = r'''    if route:

        rows = query_db(
            """
            SELECT DISTINCT

                ps.id,
                GROUP_CONCAT(DISTINCT we.wmata_stop_id),
                ps.primary_name,
                ps.latitude AS lat,
                ps.longitude AS lon,
                io.opportunity_score,

                CASE
                    WHEN io.opportunity_score >= 80 THEN 'very_high'
                    WHEN io.opportunity_score >= 60 THEN 'high'
                    WHEN io.opportunity_score >= 40 THEN 'medium'
                    ELSE 'low'
                END,

                CASE
                    WHEN io.opportunity_score >= 80 THEN 'very_high'
                    WHEN io.opportunity_score >= 60 THEN 'high'
                    WHEN io.opportunity_score >= 40 THEN 'medium'
                    ELSE 'low'
                END,

                COALESCE(
                    ca.confidence,
                    'needs_validation'
                ),

                'none'

            FROM physical_stops ps

            JOIN stop_transit_evidence ste
                ON ps.id = ste.stop_id
                AND ste.gtfs_bus_stop = 1

            JOIN improvement_opportunities io
                ON ps.id = io.physical_stop_id

            JOIN physical_stop_members psm
                ON ps.id = psm.physical_stop_id

            JOIN bus_stops bs
                ON psm.bus_stop_id = bs.id

            JOIN stop_routes sr
                ON bs.id = sr.stop_id

            LEFT JOIN stop_wmata_evidence we
                ON ps.id = we.physical_stop_id

            LEFT JOIN stop_consensus ca
                ON ps.id = ca.stop_id

            LEFT JOIN stop_jurisdiction sj
                ON ps.id = sj.stop_id

            WHERE sr.route_id = ?

            GROUP BY
                ps.id

            ORDER BY io.opportunity_score DESC;

            """,
            (
                route,
            )
        )

'''

newtext = text[:start] + replacement + text[end:]

path.write_text(newtext)

print("Fixed route map query")
print("Backup:", backup)
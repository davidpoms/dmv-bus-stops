from pathlib import Path
import re


path = Path("src/api/app.py")

text = path.read_text(encoding="utf-8")


# Add WMATA join if missing inside map_stops only
old = """
            LEFT JOIN stop_consensus ca
                ON ps.id = ca.stop_id

            JOIN physical_stop_members psm
"""

new = """
            LEFT JOIN stop_consensus ca
                ON ps.id = ca.stop_id

            LEFT JOIN stop_wmata_evidence we
                ON ps.id = we.physical_stop_id

            JOIN stop_transit_evidence ste
                ON ps.id = ste.stop_id
                AND ste.gtfs_bus_stop = 1

            JOIN physical_stop_members psm
"""


if old not in text:
    raise Exception("Could not find join insertion point")


text = text.replace(old, new, 1)


# Replace WMATA select
text = text.replace(
"""
                we.wmata_stop_id,
""",
"""
                GROUP_CONCAT(DISTINCT we.wmata_stop_id),
""",
2
)


# Add group by before ORDER BY in map queries
text = text.replace(
"""
            ORDER BY io.opportunity_score DESC;
""",
"""
            GROUP BY
                ps.id,
                ps.primary_name,
                ps.latitude,
                ps.longitude,
                io.opportunity_score,
                ca.confidence

            ORDER BY io.opportunity_score DESC;
""",
2
)


# Replace JSON output
old_json = """
                        "stop_id": row[0],
                        "wmata_stop_id": row[1],
                        "location": row[2],
"""


new_json = """
                        "stop_id": row[0],
                        "wmata_stop_ids": (
                            row[1].split(",")
                            if row[1]
                            else []
                        ),
                        "location": row[2],
"""


if old_json not in text:
    raise Exception("Could not find JSON block")


text = text.replace(old_json,new_json,1)


path.write_text(text,encoding="utf-8")

print("Map endpoint updated:")
print("- only active GTFS stops")
print("- one marker per physical stop")
print("- WMATA IDs aggregated")
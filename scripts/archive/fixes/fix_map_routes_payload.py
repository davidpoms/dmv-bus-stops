from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text(encoding="utf-8")


old = """
                ps.id,
                GROUP_CONCAT(DISTINCT we.wmata_stop_id),
                ps.primary_name,
                ps.latitude AS lat,
                ps.longitude AS lon,
                io.opportunity_score,
"""


new = """
                ps.id,
                GROUP_CONCAT(DISTINCT we.wmata_stop_id),
                ps.primary_name,
                ps.latitude AS lat,
                ps.longitude AS lon,
                io.opportunity_score,
                GROUP_CONCAT(DISTINCT r.route_name) AS routes,
"""


if old not in text:
    raise SystemExit("Could not find map SELECT block")


text = text.replace(old, new)


old_join = """
            JOIN stop_routes sr
                ON bs.id = sr.stop_id

            LEFT JOIN stop_wmata_evidence we
"""


new_join = """
            JOIN stop_routes sr
                ON bs.id = sr.stop_id

            LEFT JOIN routes r
                ON sr.route_id = r.id

            LEFT JOIN stop_wmata_evidence we
"""


if old_join not in text:
    raise SystemExit("Could not find route join block")


text = text.replace(old_join, new_join)


# second map query path
old_join2 = """
            LEFT JOIN physical_stop_members psm
                ON ps.id = psm.physical_stop_id

            LEFT JOIN stop_wmata_evidence we
"""


new_join2 = """
            LEFT JOIN physical_stop_members psm
                ON ps.id = psm.physical_stop_id

            LEFT JOIN bus_stops bs
                ON psm.bus_stop_id = bs.id

            LEFT JOIN stop_routes sr
                ON bs.id = sr.stop_id

            LEFT JOIN routes r
                ON sr.route_id = r.id

            LEFT JOIN stop_wmata_evidence we
"""


if old_join2 not in text:
    raise SystemExit("Could not find second map join block")


text = text.replace(old_join2, new_join2)


# add route to GeoJSON properties
old_props = """
                    "wmata_stop_ids":
                        row[1].split(",")
                        if row[1]
                        else []
                },
"""


new_props = """
                    "wmata_stop_ids":
                        row[1].split(",")
                        if row[1]
                        else [],

                    "routes":
                        row[7].split(",")
                        if row[7]
                        else []
                },
"""


if old_props not in text:
    raise SystemExit("Could not find GeoJSON property block")


text = text.replace(old_props, new_props)


path.write_text(text, encoding="utf-8")

print("Patched map route payload")
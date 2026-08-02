from pathlib import Path

p = Path("scripts/import_prince_georges_centerlines.py")

text = p.read_text(encoding="utf-8")

text = text.replace(
"""
            INSERT INTO road_centerlines
            (
                source,
                county,
                road_name,
                road_class,
                speed_limit,
                lanes,
                geometry
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
""",
"""
            INSERT INTO road_centerlines
            (
                source,
                road_name,
                road_class,
                speed_limit,
                lanes,
                geometry
            )
            VALUES (?, ?, ?, ?, ?, ?)
"""
)

text = text.replace(
"""
                "prince_georges",
                "Prince George's",
                row.get("fullname"),
                row.get("rdtype") or row.get("fcc"),
                int(float(row["speed"])) if row.get("speed") else None,
                None,
                json.dumps(geom)
""",
"""
                "prince_georges",
                row.get("fullname"),
                row.get("rdtype") or row.get("fcc"),
                int(float(row["speed"])) if row.get("speed") else None,
                None,
                json.dumps(geom)
"""
)

p.write_text(text, encoding="utf-8")

print("Fixed Prince George's centerline importer")
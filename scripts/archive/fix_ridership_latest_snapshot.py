from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()


old = """
        JOIN ridership_snapshots rs
            ON r.route_id = rs.route_id

        WHERE sr.stop_id = ?

        GROUP BY sr.stop_id
"""


new = """
        JOIN ridership_snapshots rs
            ON r.route_id = rs.route_id

        WHERE sr.stop_id = ?

        AND rs.period = (
            SELECT MAX(period)
            FROM ridership_snapshots
        )

        GROUP BY sr.stop_id
"""


if old not in text:
    raise Exception("Could not find ridership snapshot query block")


text = text.replace(old, new)


p.write_text(text)

print("Updated ridership query to use latest snapshot only")

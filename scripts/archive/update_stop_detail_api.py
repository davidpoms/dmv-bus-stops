from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

old = """
        SELECT
            ps.primary_name,
            sii.opportunity_score,
            sii.impact_level

        FROM physical_stops ps
"""

new = """
        SELECT
            ps.primary_name,
            ps.latitude,
            ps.longitude,
            sii.opportunity_score,
            sii.impact_level

        FROM physical_stops ps
"""

text = text.replace(old, new, 1)


old_return = """
            "stop": stop[0] if stop else None,
"""

new_return = """
            "stop":
                {
                    "location": stop[0],
                    "lat": stop[1],
                    "lon": stop[2],
                    "score": stop[3],
                    "impact": stop[4]
                }
                if stop else None,
"""

text = text.replace(old_return, new_return, 1)

p.write_text(text)

print("Updated stop detail API")

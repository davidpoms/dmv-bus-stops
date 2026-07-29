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

if old in text:
    text = text.replace(old, new, 1)
    p.write_text(text)
    print("Fixed stop detail SQL query")
else:
    print("Query block not found")

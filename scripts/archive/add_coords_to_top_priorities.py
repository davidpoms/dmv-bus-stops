from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

text = text.replace(
"""
            ps.primary_name,
            sii.opportunity_score,
            sii.priority_level,
            sii.impact_level
""",
"""
            ps.primary_name,
            ps.latitude,
            ps.longitude,
            sii.opportunity_score,
            sii.priority_level,
            sii.impact_level
""",
1
)

text = text.replace(
"""
                "location": row[0],
                "score": row[1],
                "priority": row[2],
                "impact": row[3]
""",
"""
                "location": row[0],
                "lat": row[1],
                "lon": row[2],
                "score": row[3],
                "priority": row[4],
                "impact": row[5]
""",
1
)

p.write_text(text)

print("Added coordinates to top priorities")

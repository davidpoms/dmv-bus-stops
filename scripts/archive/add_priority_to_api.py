from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

# Add priority_level to SELECT statements
text = text.replace(
    """
                sii.opportunity_score,
                sii.impact_level
""",
    """
                sii.opportunity_score,
                sii.impact_level,
                sii.priority_level
"""
)

# Add priority to JSON output
text = text.replace(
    """
                        "score": row[4],
                        "impact": row[5]
""",
    """
                        "score": row[4],
                        "impact": row[5],
                        "priority": row[6]
"""
)

p.write_text(text)

print("Added priority_level to API output")

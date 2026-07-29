from pathlib import Path

p = Path("src/assessment/calculate_recommendation_confidence.py")

text = p.read_text()

text = text.replace(
    "COUNT(sr.id)",
    "COUNT(o.id)"
)

text = text.replace(
    """
        LEFT JOIN stop_reviews sr

            ON io.physical_stop_id = sr.stop_id
""",
    """
        LEFT JOIN stop_observations o

            ON io.physical_stop_id = o.physical_stop_id
"""
)

p.write_text(text)

print("Migrated recommendation confidence to stop_observations")

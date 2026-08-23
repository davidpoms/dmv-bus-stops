from pathlib import Path

p = Path("src/assessment/generate_impact_summary.py")

text = p.read_text()

old = """        if opportunity_score >= 85:

            impact_level = "very_high"

        elif opportunity_score >= 70:

            impact_level = "high"

        elif opportunity_score >= 50:

            impact_level = "medium"

        else:

            impact_level = "low"
"""

new = """        if opportunity_score >= 75:

            impact_level = "very_high"

        elif opportunity_score >= 60:

            impact_level = "high"

        elif opportunity_score >= 45:

            impact_level = "medium"

        else:

            impact_level = "low"
"""

if old not in text:
    print("Threshold block not found")
    exit(1)

text = text.replace(old, new)

p.write_text(text)

print("Impact thresholds updated")

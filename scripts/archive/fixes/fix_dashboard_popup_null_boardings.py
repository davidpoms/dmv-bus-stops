from pathlib import Path

path = Path("src/dashboard/static/dashboard.js")

text = path.read_text(encoding="utf-8")

old = """detail.impact_summary
                                    ? detail.impact_summary.estimated_weekday_boardings.toLocaleString()
                                    : "Unknown"
"""

new = """detail.impact_summary &&
                                    detail.impact_summary.estimated_weekday_boardings !== null &&
                                    detail.impact_summary.estimated_weekday_boardings !== undefined
                                    ? detail.impact_summary.estimated_weekday_boardings.toLocaleString()
                                    : "Unknown"
"""

if old not in text:
    raise SystemExit(
        "Target text not found. No changes made."
    )

text = text.replace(old, new)

path.write_text(text, encoding="utf-8")

print("Updated dashboard popup null handling.")
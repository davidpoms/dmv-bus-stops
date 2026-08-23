from pathlib import Path

p = Path("scripts/build_dashboard_geography_tables.py")

text = p.read_text()

text = text.replace(
    "jurisdiction AS state",
    "state"
)

text = text.replace(
    "GROUP BY\n    jurisdiction,",
    "GROUP BY\n    state,"
)

p.write_text(text)

print("Restored geography builder to use stop_jurisdiction.state")

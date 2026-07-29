from pathlib import Path

p = Path("scripts/build_dashboard_geography_tables.py")

text = p.read_text()

text = text.replace(
    "state,",
    "jurisdiction AS state,"
)

text = text.replace(
    "GROUP BY state, county",
    "GROUP BY jurisdiction, county"
)

text = text.replace(
    "GROUP BY state, county, municipality",
    "GROUP BY jurisdiction, county, municipality"
)

p.write_text(text)

print("Updated geography builder to use jurisdiction")

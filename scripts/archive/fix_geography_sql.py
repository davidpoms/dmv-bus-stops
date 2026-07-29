from pathlib import Path

p = Path("scripts/build_dashboard_geography_tables.py")

text = p.read_text()

text=text.replace(
    "GROUP BY\n    jurisdiction AS state,",
    "GROUP BY\n    jurisdiction,"
)

p.write_text(text)

print("Fixed GROUP BY aliases")

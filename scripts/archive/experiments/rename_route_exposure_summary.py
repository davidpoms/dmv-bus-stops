from pathlib import Path

path = Path("src/assessment/generate_impact_summary.py")

text = path.read_text()

text = text.replace(
    'f"{round(daily_route_exposure):,} weekday riders across serving routes."',
    'f"{round(daily_route_exposure):,} combined weekday boardings across serving routes."'
)

path.write_text(text)

print("Updated impact summary wording")

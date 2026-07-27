from pathlib import Path

files = [
    Path("src/assessment/generate_impact_summary.py"),
]

replacements = {
    "daily_riders": "daily_route_exposure",
    "daily weekday riders": "weekday riders across serving routes",
    "Bus stop serving ": "Bus stop with ",
}

for path in files:
    text = path.read_text()

    original = text

    for old, new in replacements.items():
        text = text.replace(old, new)

    if text != original:
        path.write_text(text)
        print(f"Updated {path}")
    else:
        print(f"No changes needed: {path}")

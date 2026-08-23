from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

print("\n=== Dashboard Frontend Debug ===\n")

# Find JS files
print("Searching for JavaScript assets...\n")

js_files = list(ROOT.rglob("dashboard.js")) + list(ROOT.rglob("review.js"))

if js_files:
    for f in js_files:
        print(f"FOUND: {f.relative_to(ROOT)}")
else:
    print("NO dashboard.js or review.js files found")

print("\n=== Generated Dashboard Checks ===\n")

dashboard = ROOT / "dmv_bus_stops_dashboard.html"

if not dashboard.exists():
    print("ERROR: dmv_bus_stops_dashboard.html not found")
else:
    text = dashboard.read_text(encoding="utf-8", errors="replace")

    print("Dashboard file found")

    # Map checks
    print("\nMap references:")

    map_lines = [
        line.strip()
        for line in text.splitlines()
        if "map" in line.lower()
    ]

    if map_lines:
        for line in map_lines[:20]:
            print(line)
    else:
        print("No map references found")

    # Leaflet checks
    print("\nLeaflet references:")

    leaflet_lines = [
        line.strip()
        for line in text.splitlines()
        if "leaflet" in line.lower()
    ]

    if leaflet_lines:
        for line in leaflet_lines[:20]:
            print(line)
    else:
        print("No Leaflet references found")

    # Charset check
    print("\nEncoding check:")

    if "charset=UTF-8" in text or 'charset="UTF-8"' in text:
        print("UTF-8 charset declaration found")
    else:
        print("WARNING: No UTF-8 charset declaration found")

    # Review counts
    print("\nReview pipeline status:")

    for phrase in [
        "Completed reviews",
        "Pending assignments",
        "Stops reaching consensus",
        "Stops identified"
    ]:
        if phrase in text:
            idx = text.find(phrase)
            print(text[idx:idx+120].replace("\n", " "))

print("\n=== Static Directory ===\n")

static = ROOT / "static"

if static.exists():
    print("static/ exists")
    for f in static.rglob("*"):
        print(f.relative_to(ROOT))
else:
    print("WARNING: static/ directory missing")

print("\n=== Done ===")

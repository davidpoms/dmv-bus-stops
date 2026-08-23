from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text(encoding="utf-8")

old = """JOIN stop_transit_evidence ste
                ON ps.id = ste.stop_id
                AND ste.gtfs_bus_stop = 1"""

new = """JOIN active_wmata_evidence aw
                ON ps.id = aw.physical_stop_id"""

count = text.count(old)

if count == 0:
    raise SystemExit(
        "No matching stop_transit_evidence join found. "
        "Nothing changed."
    )

text = text.replace(old, new)

path.write_text(text, encoding="utf-8")

print(f"Updated {count} map query joins.")
print("src/api/app.py patched successfully.")
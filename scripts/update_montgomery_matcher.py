from pathlib import Path

FILE = Path(
    "scripts/import_montgomery_amenities.py"
)

text = FILE.read_text()

text = text.replace(
    "find_nearest_physical_stop",
    "find_nearest_wmata_stop"
)

FILE.write_text(text)

print(
    "Updated Montgomery importer to use WMATA matcher"
)
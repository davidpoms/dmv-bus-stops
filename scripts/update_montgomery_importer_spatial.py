from pathlib import Path

FILE = Path(
    "scripts/import_montgomery_amenities.py"
)

text = FILE.read_text()


# Replace outSR formatting
text = text.replace(
    '"outSR": 4326,',
    '"outSR": "4326",'
)


# Add returnTrueCurves if missing
if '"returnTrueCurves"' not in text:
    text = text.replace(
        '"returnGeometry": "true",',
        '"returnGeometry": "true",\n    "returnTrueCurves": "false",'
    )


FILE.write_text(text)

print(
    "Updated Montgomery importer spatial settings"
)
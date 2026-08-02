from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

# Only fix remaining map_stops alias mismatch
replacements = {
    "sv.confidence": "ca.confidence",
    "sv.status": "ca.confidence",
    "sv.id": "ca.id",
    "sv.physical_stop_id": "ca.stop_id",
}

for old, new in replacements.items():
    text = text.replace(old, new)

p.write_text(text)

print("patched map_stops consensus aliases")
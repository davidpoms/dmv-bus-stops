from pathlib import Path

path = Path("scripts/download_wmata_stops.py")

text = path.read_text()

text = text.replace(
    'print(f"SPLIT FAILED RANGE {start}-{end}")',
    'log.append((start,end))'
)

text = text.replace(
    'SKIPPING BAD OBJECTID:',
    'SKIP'
)

if "log = []" not in text:
    text = text.replace(
        "OUT = Path",
        "log = []\n\nOUT = Path"
    )

text += """

# Write failed ranges after completion
with open("data/wmata_failed_ranges.log", "w") as f:
    for item in log:
        f.write(f"{item[0]}-{item[1]}\\\\n")
"""

path.write_text(text)

print("patched", path)

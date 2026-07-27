from pathlib import Path
import re

text = Path("src/api/app.py").read_text()

m = re.search(
    r'INSERT INTO stop_observations\s*\((.*?)\)\s*VALUES\s*\((.*?)\)\s*""",\s*\((.*?)\)\s*\)',
    text,
    re.S,
)

if not m:
    raise Exception("Couldn't locate INSERT block")

columns = [
    c.strip().strip(",")
    for c in m.group(1).splitlines()
    if c.strip() and not c.strip().startswith("(")
]

values = [
    line.strip().rstrip(",")
    for line in m.group(3).splitlines()
    if line.strip()
    and not line.strip().startswith("#")
    and not line.strip().startswith(")")
]

print(f"Columns: {len(columns)}")
print(f"Values : {len(values)}")
print()

for i in range(max(len(columns), len(values))):
    col = columns[i] if i < len(columns) else "<<MISSING COLUMN>>"
    val = values[i] if i < len(values) else "<<MISSING VALUE>>"
    print(f"{i+1:2d}. {col:28} -> {val}")

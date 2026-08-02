from pathlib import Path
from datetime import datetime

path = Path("src/dashboard/templates/review.html")

text = path.read_text()

backup = path.with_name(
    path.stem +
    ".bak_" +
    datetime.now().strftime("%Y%m%d_%H%M%S") +
    path.suffix
)

backup.write_text(text)

old = 'params.get("assignment")'
new = 'params.get("assignment_id")'

if old not in text:
    print("Could not find old assignment parameter")
    exit()

text = text.replace(old, new, 1)

path.write_text(text)

print("Fixed review.html assignment parameter")
print("Backup:", backup)
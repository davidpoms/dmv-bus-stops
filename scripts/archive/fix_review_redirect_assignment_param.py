from pathlib import Path
from datetime import datetime

path = Path("src/api/app.py")

text = path.read_text()

backup = path.with_suffix(
    ".py.bak_" + datetime.now().strftime("%Y%m%d_%H%M%S")
)

backup.write_text(text)

old = 'f"/review/{stop_id}?assignment={assignment_id}&mode={scenario}"'

new = 'f"/review/{stop_id}?assignment_id={assignment_id}&mode={scenario}"'

if old not in text:
    print("Could not find redirect")
    exit()

text = text.replace(old, new, 1)

path.write_text(text)

print("Fixed assignment_id redirect")
print("Backup:", backup)
from pathlib import Path
import shutil
import re

path = Path("src/api/app.py")

if not path.exists():
    raise SystemExit("src/api/app.py not found")

text = path.read_text(encoding="utf-8")

pattern = r"sr\.route_id\s*=\s*r\.route_id"
replacement = "sr.route_id = r.id"

matches = len(re.findall(pattern, text))

if matches == 0:
    print("No route joins found.")
    raise SystemExit(0)

backup = path.with_suffix(".py.route_join_backup")
shutil.copy2(path, backup)

text = re.sub(pattern, replacement, text)

path.write_text(text, encoding="utf-8")

print(f"Updated {matches} route joins")
print(f"Backup saved to {backup}")
from pathlib import Path
import re

p = Path("src/database/schema.sql")
text = p.read_text()

pattern = r"(CREATE TABLE IF NOT EXISTS stop_observations\s*\(.*?\n\);)"

matches = list(re.finditer(pattern, text, flags=re.S))

if len(matches) <= 1:
    print("Nothing to deduplicate.")
    raise SystemExit

first = matches[0].group(1)

# Remove all copies
text = re.sub(pattern, "", text, flags=re.S)

# Insert the canonical definition where the first one originally appeared
insert_at = matches[0].start()
text = text[:insert_at] + first + "\n\n" + text[insert_at:]

p.write_text(text)

print(f"Removed {len(matches)-1} duplicate stop_observations definitions")

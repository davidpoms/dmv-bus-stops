from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

lines = p.read_text().splitlines()

# remove the current standalone `);` before the final `});`
for i, line in enumerate(lines):
    if i > 1200 and line.strip() == ");" and i + 2 <= len(lines):
        if lines[i+2].strip() == "});":
            print("Removing line", i+1)
            del lines[i]
            break
else:
    raise SystemExit("Could not find stray );")

p.write_text("\n".join(lines) + "\n")

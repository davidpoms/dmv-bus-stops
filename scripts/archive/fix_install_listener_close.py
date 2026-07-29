from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

lines = p.read_text().splitlines()

# Find the final listener close pattern and insert missing function brace
for i in range(len(lines)-1, -1, -1):
    if lines[i].strip() == ");":
        if i > 0 and lines[i-1].strip() == "}":
            lines.insert(i, "        }")
            break
else:
    raise SystemExit("Could not find final );")

p.write_text("\n".join(lines) + "\n")

print("inserted missing listener brace")

from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

lines = p.read_text().splitlines()

# remove the duplicate brace directly after the .then callback close
for i in range(len(lines)):
    if (
        i > 0
        and lines[i].strip() == "}"
        and lines[i-1].strip() == "}"
        and i > 1200
    ):
        del lines[i]
        print("removed bad inserted brace at", i+1)
        break
else:
    raise SystemExit("bad brace not found")

p.write_text("\n".join(lines) + "\n")

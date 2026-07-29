from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

lines = p.read_text().splitlines()

# Remove the extra brace at the current known location
if lines[682].strip() == "}":
    del lines[682]
else:
    raise SystemExit(
        f"Unexpected line 683: {lines[682]!r}"
    )

p.write_text("\n".join(lines) + "\n")

print("removed line 683")

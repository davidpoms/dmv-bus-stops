from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

lines = p.read_text().splitlines()

if lines[-1].strip() == "});":
    lines.pop()
else:
    raise SystemExit(f"Unexpected last line: {lines[-1]!r}")

p.write_text("\n".join(lines) + "\n")

print("removed extra final });")

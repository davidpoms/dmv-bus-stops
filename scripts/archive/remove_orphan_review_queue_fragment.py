from pathlib import Path

path = Path("src/dashboard/static/dashboard.js")

text = path.read_text()

start_marker = "// -------------------------------\n// Review queue loader\n// -------------------------------"

start = text.find(start_marker)

if start == -1:
    raise SystemExit("Orphan review queue marker not found")


end_marker = "// -----------------------------\n// Pipeline table"

end = text.find(end_marker, start)

if end == -1:
    raise SystemExit("Pipeline table marker not found")


text = text[:start] + text[end:]

path.write_text(text)

print("Removed orphan review queue fragment")

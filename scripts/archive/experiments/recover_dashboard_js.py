from pathlib import Path

src = Path("src/dashboard/generate_dashboard_backup.py")
out = Path("src/dashboard/static/dashboard.js")

text = src.read_text()

scripts = []

start = 0
while True:
    pos = text.find("<script", start)
    if pos == -1:
        break
    scripts.append(pos)
    start = pos + 1

print("Found script tags:", scripts)

if len(scripts) < 2:
    raise SystemExit("Expected at least two script tags")

start = scripts[1]
end = text.find("</script>", start)

if end == -1:
    raise SystemExit("Closing script tag not found")

block = text[start:end]

js_start = block.find(">") + 1
js = block[js_start:]

out.write_text(js.strip() + "\n")

print("Recovered characters:", len(js))

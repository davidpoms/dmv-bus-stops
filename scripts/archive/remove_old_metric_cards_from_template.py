from pathlib import Path

p = Path("src/dashboard/templates/dashboard.html")

text = p.read_text()

start = text.find("<h2>Consensus Verification Pipeline</h2>")

if start == -1:
    raise SystemExit("Old metric section not found")

start = text.rfind('<div class="card">', 0, start)

end = text.find("<h2>Community Review Network</h2>", start)

if end == -1:
    raise SystemExit("Community Review Network not found")

end = text.rfind('<div class="card">', 0, end)

text = text[:start] + text[end:]

p.write_text(text)

print("Removed old dashboard metric cards")

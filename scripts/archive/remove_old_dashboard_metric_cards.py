from pathlib import Path

path = Path("src/dashboard/templates/dashboard.html")

text = path.read_text()


sections = [
    ("<h2>Consensus Verification Pipeline</h2>",
     "<h2>Community Review Network</h2>")
]


for start_marker, end_marker in sections:

    start = text.find(start_marker)

    if start == -1:
        raise SystemExit(f"Missing {start_marker}")

    # remove enclosing card start
    start = text.rfind('<div class="card">', 0, start)

    end = text.find(end_marker, start)

    if end == -1:
        raise SystemExit(f"Missing {end_marker}")

    text = text[:start] + text[end:]


path.write_text(text)

print("Removed old dashboard metric cards")

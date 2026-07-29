from pathlib import Path

path = Path("src/dashboard/static/dashboard.js")

text = path.read_text()

start = text.find(
"function loadReviewQueue(){"
)

if start == -1:
    raise SystemExit("loadReviewQueue not found")


end = text.find(
"\n\n\n",
start
)

if end == -1:
    raise SystemExit("Could not find end")


text = text[:start] + text[end+3:]

path.write_text(text)

print("Removed loadReviewQueue function")

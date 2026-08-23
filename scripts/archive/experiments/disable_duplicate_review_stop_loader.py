from pathlib import Path

for p in [
    Path("src/dashboard/templates/review.html"),
    Path("src/dashboard/templates/review_stop.html"),
]:

    if not p.exists():
        continue

    text = p.read_text()

    text = text.replace(
        '<script src="/static/review_stop.js"></script>',
        '<!-- disabled duplicate review_stop.js -->'
    )

    p.write_text(text)

print("Disabled duplicate review_stop loader")

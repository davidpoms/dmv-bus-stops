from pathlib import Path

p = Path("src/dashboard/templates/dashboard.html")

text = p.read_text()

tag = '<script src="/static/review.js"></script>'

if tag not in text:
    text = text.replace(
        '<script src="/static/dashboard.js"></script>',
        '<script src="/static/dashboard.js"></script>\n' + tag
    )

    p.write_text(text)
    print("Added review.js include")

else:
    print("Already included")

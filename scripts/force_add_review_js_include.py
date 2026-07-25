from pathlib import Path

p = Path("src/dashboard/templates/dashboard.html")

text = p.read_text()

tag = '<script src="/static/review.js"></script>'

if tag not in text:
    text += "\n" + tag + "\n"
    p.write_text(text)
    print("Forced review.js include")
else:
    print("review.js already present")

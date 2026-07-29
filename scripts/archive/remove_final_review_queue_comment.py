from pathlib import Path

path = Path("src/dashboard/static/dashboard.js")

text = path.read_text()

comment = "// -----------------------------\n// Review Queue"

if text.rstrip().endswith(comment):
    text = text.rstrip()
    text = text[:text.rfind(comment)].rstrip() + "\n"
    path.write_text(text)
    print("Removed final dangling Review Queue comment")
else:
    print("No dangling Review Queue comment found")

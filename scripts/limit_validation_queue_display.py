from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

text = text.replace(
    "data.forEach(stop =>",
    "data.slice(0,10).forEach(stop =>",
    1
)

p.write_text(text)

print("Limited validation queue to 10 items")

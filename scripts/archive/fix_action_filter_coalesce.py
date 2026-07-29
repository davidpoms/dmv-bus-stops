from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

text = text.replace(
    "OR ca.status = ?",
    "OR COALESCE(ca.status, 'none') = ?"
)

p.write_text(text)

print("action filter coalesce fixed")

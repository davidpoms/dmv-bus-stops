from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text(encoding="utf-8")

text = text.replace(
    r'\n\n@app.route("/dashboard")',
    '\n\n@app.route("/dashboard")'
)

p.write_text(text, encoding="utf-8")

print("fixed")
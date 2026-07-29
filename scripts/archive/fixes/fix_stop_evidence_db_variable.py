from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

text = text.replace(
    "conn = sqlite3.connect(DATABASE)",
    "conn = sqlite3.connect(DATABASE_PATH)"
)

text = text.replace(
    "conn = sqlite3.connect(DB)",
    "conn = sqlite3.connect(DATABASE_PATH)"
)

p.write_text(text)

print("Fixed evidence endpoint database variable")

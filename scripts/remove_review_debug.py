from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

text = text.replace(
'''    print("NORMALIZED REVIEW MODE:", data.get("review_mode"))
    print("FULL NORMALIZED DATA:", data)

''',
''
)

p.write_text(text)

print("Removed review debug")

from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

first = text.find("const map = L.map")
second = text.find("const map = L.map", first + 1)

if second != -1:
    text = text[:second]
    p.write_text(text)
    print("Removed duplicate dashboard.js section")
else:
    print("No duplicate found")

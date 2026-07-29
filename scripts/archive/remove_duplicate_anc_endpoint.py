from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

first = text.find('@app.route("/geography/dc-ancs")')
second = text.find('@app.route("/geography/dc-ancs")', first + 1)

if first == -1 or second == -1:
    raise Exception("Could not find duplicate ANC routes")

# Find end of first function before next route
end = text.find('@app.route', first + 1)

if end == -1:
    raise Exception("Could not find end of first ANC endpoint")

text = text[:first] + text[end:]

p.write_text(text)

print("Removed duplicate ANC endpoint")

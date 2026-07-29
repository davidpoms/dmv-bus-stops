from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()

old = """
def submit_review():

    data = request.json
"""

new = """
def submit_review():

    data = request.json

    print("DEBUG REVIEW PAYLOAD:")
    print(data)
"""

if "DEBUG REVIEW PAYLOAD:" in text:
    print("Already added")
    raise SystemExit

if old not in text:
    raise SystemExit("Could not find submit_review block")

text = text.replace(old, new)

path.write_text(text)

print("Added debug logging")

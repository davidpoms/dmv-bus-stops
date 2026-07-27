from pathlib import Path
import re

text = Path("src/api/app.py").read_text()

start = text.find('@app.route("/review/submit"')
end = text.find('@app.route(', start + 10)

block = text[start:end]

columns = re.search(
    r'INSERT INTO stop_observations\s*\((.*?)\)\s*VALUES',
    block,
    re.S
)

placeholders = re.search(
    r'VALUES\s*\((.*?)\)',
    block,
    re.S
)

if not columns or not placeholders:
    raise Exception("Could not find INSERT block")

cols = [
    x.strip()
    for x in columns.group(1).split(",")
    if x.strip()
]

marks = [
    x.strip()
    for x in placeholders.group(1).split(",")
    if x.strip()
]

print("Columns:", len(cols))
print("Placeholders:", len(marks))

for i, c in enumerate(cols, 1):
    print(i, c)


from pathlib import Path
import re

p = Path("src/api/app.py")

text = p.read_text()

# Only operate inside submit_review()
start = text.find('@app.route("/review/submit"')

if start == -1:
    raise Exception("submit_review route not found")

end = text.find('@app.route(', start + 10)

if end == -1:
    end = len(text)

section = text[start:end]

old = re.compile(
    r'VALUES\s*\(\s*'
    r'(\?,\s*){24}\?\s*'
    r'\)',
    re.S
)

match = old.search(section)

if not match:
    # print nearby VALUES blocks for debugging
    print(section[section.find("VALUES"):section.find("VALUES")+300])
    raise Exception("Could not find 25-placeholder VALUES block")

replacement = """VALUES
        (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

section = section[:match.start()] + replacement + section[match.end():]

text = text[:start] + section + text[end:]

p.write_text(text)

print("Fixed submit_review placeholder count to 24")

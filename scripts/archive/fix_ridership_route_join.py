from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

old = """
        JOIN routes r
            ON sr.route_id = r.id
"""

new = """
        JOIN routes r
            ON sr.route_id = r.route_id
"""

if old not in text:
    raise Exception("Could not find incorrect routes join")

text = text.replace(old, new)

p.write_text(text)

print("Fixed ridership route join")

from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

old = """
let reviewMode = "";
"""

new = """
let reviewMode = "";

let actionFilter = "";
"""

if old not in text:
    print("state anchor not found")
    raise SystemExit(1)

text = text.replace(old,new,1)

p.write_text(text)

print("action filter state added")

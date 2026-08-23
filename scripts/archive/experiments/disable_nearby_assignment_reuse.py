from pathlib import Path

path = Path("src/review/assignment_router.py")

text = path.read_text()

old = """    if existing:
        conn.close()
        return existing[0], existing[1]
"""

new = """    if existing and scenario == "opportunity":
        conn.close()
        return existing[0], existing[1]
"""

if old not in text:
    raise Exception("reuse block not found")

text=text.replace(old,new)

path.write_text(text)

print("Disabled reuse for route/nearby")

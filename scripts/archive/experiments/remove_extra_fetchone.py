from pathlib import Path

path = Path("src/review/assignment_router.py")

text = path.read_text()

bad = """
        ).fetchone()




        ).fetchone()
"""

good = """
        ).fetchone()
"""

if bad not in text:
    raise Exception("Could not find duplicate fetchone block")

text = text.replace(bad, good, 1)

path.write_text(text)

print("Removed extra fetchone")
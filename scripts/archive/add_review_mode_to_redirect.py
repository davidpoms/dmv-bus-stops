from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

old = """
    return redirect(
        f"/review/{stop_id}?assignment={assignment_id}"
    )
"""

new = """
    return redirect(
        f"/review/{stop_id}?assignment={assignment_id}&mode={scenario}"
    )
"""

if old not in text:
    raise Exception("redirect block not found")

text = text.replace(old, new)

p.write_text(text)

print("added mode to review redirect")
from pathlib import Path

p = Path("src/dashboard/generate_dashboard.py")

text = p.read_text()

needle = "PARTIAL_ROUTES="

idx = text.find(needle)

if idx == -1:
    raise Exception("Could not find PARTIAL_ROUTES")

line_end = text.find("\n", idx)

line = text[idx:line_end]

addition = """
        COMPLETED_REVIEWS=f"{metrics['consensus']['completed_reviews']:,}",
        PENDING_REVIEWS=f"{metrics['consensus']['pending_reviews']:,}",
        VERIFIED_STOPS=f"{metrics['consensus']['verified_stops']:,}",
"""

text = (
    text[:line_end+1]
    + addition
    + text[line_end+1:]
)

p.write_text(text)

print("Added consensus variables")

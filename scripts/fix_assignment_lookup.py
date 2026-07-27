from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

text = text.replace(
"""
        WHERE stop_id=?

        AND status='assigned'
""",
"""
        WHERE stop_id=?
"""
)

p.write_text(text)

print("Updated assignment lookup")

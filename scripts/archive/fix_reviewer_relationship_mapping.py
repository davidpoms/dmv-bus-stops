from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

old = '''
        # Reviewer identity/context
        "reviewer_relationship":
            "observer",


'''

if old not in text:
    raise Exception("Reviewer relationship mapping not found")

text = text.replace(old, "")

p.write_text(text)

print("Removed reviewer_relationship -> observer mapping")

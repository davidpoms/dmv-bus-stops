from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

target = '''
@app.get("/api/reviewer/<int:reviewer_id>/queue")
'''

first = text.find(target)
second = text.find(target, first + 1)

if first == -1 or second == -1:
    raise SystemExit("Could not find duplicate reviewer queue routes")

# remove from second duplicate route until EOF
# (temporary cleanup; we'll verify afterwards)
text = text[:second]

p.write_text(text)

print("Removed duplicate reviewer route block")

from pathlib import Path


path = Path("src/dashboard/static/dashboard.js")

text = path.read_text()


needle = "function loadReviewQueue(){"


first = text.find(needle)
second = text.find(needle, first + 1)


if first == -1:
    raise SystemExit("Could not find first loadReviewQueue function")

if second == -1:
    raise SystemExit("Could not find second loadReviewQueue function")


# Remove from second function to end of file
new_text = text[:second].rstrip() + "\n"


path.write_text(new_text)

print("Removed duplicate Review Queue loader")

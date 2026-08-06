from pathlib import Path

path = Path("src/api/app.py")

text = path.read_text()

old = """    else:

        result = assign_stop(
            reviewer_id,
            scenario
        )
"""

new = """    else:

        result = assign_stop(
            reviewer_id,
            scenario,
            latitude=latitude,
            longitude=longitude
        )
"""

if old not in text:
    print("Trying whitespace-insensitive replacement...")

    start = text.find("    else:\n\n        result = assign_stop(")

    if start == -1:
        raise Exception("Could not locate else assignment block")

    end = text.find("\n\n\n    if not result:", start)

    if end == -1:
        raise Exception("Could not locate end of assignment block")

    replacement = new.rstrip()

    text = (
        text[:start]
        + replacement
        + text[end:]
    )

else:
    text = text.replace(old, new)

path.write_text(text)

print("Nearby coordinates passed into assign_stop")

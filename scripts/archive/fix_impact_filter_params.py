from pathlib import Path


p = Path("src/api/app.py")

text = p.read_text()


# Remove duplicated impact filter block in route query
duplicate = """
            AND (
                ? IS NULL
                OR (
                    ? = 'high'
                    AND sii.impact_level IN ('high', 'very_high')
                )
                OR (
                    ? = 'very_high'
                    AND sii.impact_level = 'very_high'
                )
            )
"""

first = text.find(duplicate)
second = text.find(duplicate, first + 1)

if first != -1 and second != -1:
    text = text[:second] + text[second + len(duplicate):]
    print("Removed duplicate impact filter")
else:
    print("Duplicate filter not found")


# Replace route query parameters
old = """
            (route,)
        )
"""

new = """
            (
                route,
                impact,
                impact,
                impact,
                impact
            )
        )
"""

if old in text:
    text = text.replace(old, new, 1)
    print("Fixed route query parameters")
else:
    print("Route parameter tuple not found")


# Find non-route branch and add parameters if needed later
p.write_text(text)

print("Impact filter parameter patch complete")

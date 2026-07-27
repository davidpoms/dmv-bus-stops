from pathlib import Path

p = Path("src/api/app.py")

text = p.read_text()

old = '''    data["shelter_protection"] = data.get(
        "shelter_protection",
        ""
    )

'''

text = text.replace(old, "", 1)


debug_start = '''    print(
        "INSERT DEBUG:",
'''

if debug_start in text:
    start = text.index(debug_start)
    end = text.index("    )\n\n", start) + len("    )\n\n")
    text = text[:start] + text[end:]

p.write_text(text)

print("Cleaned review normalization")

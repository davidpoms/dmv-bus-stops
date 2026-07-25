from pathlib import Path

# Remove old imports
p = Path("src/dashboard/generate_dashboard.py")
text = p.read_text()

text = text.replace(
    "    top_counties,\n",
    ""
)

text = text.replace(
    "    top_municipalities,\n",
    ""
)

p.write_text(text)


# Remove old functions
p = Path("src/dashboard/data.py")
text = p.read_text()

start = text.find("def top_counties(")

if start != -1:
    end = text.find("def ", start + 5)
    
    if end != -1:
        text = text[:start] + text[end:]
    else:
        text = text[:start]

start = text.find("def top_municipalities(")

if start != -1:
    end = text.find("def ", start + 5)

    if end != -1:
        text = text[:start] + text[end:]
    else:
        text = text[:start]

p.write_text(text)

print("Removed old top geography functions")

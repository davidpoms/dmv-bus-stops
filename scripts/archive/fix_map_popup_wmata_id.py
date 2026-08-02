from pathlib import Path
import re

path = Path("src/dashboard/static/dashboard.js")

text = path.read_text()


# Add WMATA ID after popup title
pattern = r'(<b>\$\{props\.location\.replace\("\+", " at "\)\}</b><br>)'

replacement = r'''\1

                                <b>WMATA Stop ID:</b> ${props.wmata_stop_id || "Unknown"}<br>'''

text, count = re.subn(
    pattern,
    replacement,
    text,
    count=1
)

if count == 0:
    raise Exception("Could not find popup location line")


# Fix accidental double quote in review link
text = text.replace(
    'href="/review/${props.stop_id}?mode=opportunity""',
    'href="/review/${props.stop_id}?mode=opportunity"'
)


path.write_text(text)

print("Updated dashboard popup")
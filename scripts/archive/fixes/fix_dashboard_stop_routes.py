from pathlib import Path

path = Path("src/dashboard/static/dashboard.js")

text = path.read_text()

old = """
fetch(/stops/)
"""

new = """
fetch(/review//info)
"""

if old in text:
    text = text.replace(old, new)
    print("Updated stop detail fetch endpoint")
else:
    print("Could not find fetch('/stops/') pattern")


# Replace direct browser navigation to API endpoint
old2 = """
/stops/
"""

new2 = """
/review/
"""

if old2 in text:
    text = text.replace(old2, new2)
    print("Updated stop navigation route")
else:
    print("Could not find stop navigation pattern")


path.write_text(text)

print("dashboard.js patch complete")

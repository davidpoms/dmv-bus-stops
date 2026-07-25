from pathlib import Path

p = Path("src/api/templates/reviewer_dashboard.html")

text = p.read_text()

old = 'href="/dashboard?stop={{ stop.stop_id }}"'

new = 'href="/dashboard?stop={{ stop.stop_id }}&assignment={{ stop.assignment_id }}"'

if old in text:
    text = text.replace(old, new)
    print("Updated reviewer links")
else:
    print("Dashboard stop link not found")

p.write_text(text)

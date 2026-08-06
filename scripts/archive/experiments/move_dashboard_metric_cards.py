from pathlib import Path

p = Path("src/dashboard/templates/dashboard.html")

text = p.read_text()

start = text.index('<div class="card">\n<h2>Community Verification Progress</h2>')

end = text.index('</div>\n\n\n</body>', start) + len('</div>')

cards = text[start:end]

# remove existing cards
text = text[:start] + text[end:]

# insert after dashboard title
marker = """
<h1>
DMV Bus Stop Improvement Dashboard
</h1>
"""

text = text.replace(
    marker,
    marker + "\n\n" + cards,
    1
)

p.write_text(text)

print("Moved metric cards to dashboard top")

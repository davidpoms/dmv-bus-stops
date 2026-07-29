from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

start = text.find(
"""
document
.getElementById("impactSelect")
.addEventListener(
"""
)

if start != -1:
    end = text.find(
        """
);


function loadPrioritySummary()
""",
        start
    )

    text = text[:start] + "\n\nfunction loadPrioritySummary()" + text[end + len("""

function loadPrioritySummary()"""):]

    p.write_text(text)

    print("Removed impact filter listener")
else:
    print("Impact listener not found")

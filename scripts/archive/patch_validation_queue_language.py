from pathlib import Path

p = Path("src/dashboard/templates/dashboard.html")

text = p.read_text()


text = text.replace(
"""
<h3>Stop Survey Queue</h3>

<p>
Review stops one at a time using Google Street View.
Record conditions at the stop location.
</p>
""",
"""
<h3>Help Verify Transit Improvements</h3>

<p>
Join other volunteers reviewing stops before improvements are recommended.

<br><br>

⭐ Highest opportunities
<br>

🚌 Stops on your favorite routes
<br>

📍 Stops near you

</p>
"""
)


p.write_text(text)

print("validation queue language patched")


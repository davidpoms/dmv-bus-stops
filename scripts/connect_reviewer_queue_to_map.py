from pathlib import Path

p = Path("src/api/templates/reviewer_dashboard.html")

text = p.read_text()

text = text.replace(
"""
<td>
{{ stop.stop_id }}
</td>
""",
"""
<td>
<a href="/dashboard?stop={{ stop.stop_id }}">
{{ stop.stop_id }}
</a>
</td>
"""
)

p.write_text(text)

print("Connected reviewer queue stops to dashboard map")

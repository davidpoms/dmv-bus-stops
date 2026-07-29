from pathlib import Path


p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()


# Replace marker color logic
text = text.replace(
"""
props.impact === "very_high"
""",
"""
props.priority === "P1"
"""
)

text = text.replace(
"""
props.impact === "high"
""",
"""
props.priority === "P2"
"""
)

text = text.replace(
"""
props.impact === "medium"
""",
"""
props.priority === "P3"
"""
)


# Replace legend text
text = text.replace(
"""
<b>Impact Level</b><br>

<span style="color:red;">●</span>
Very High<br>

<span style="color:orange;">●</span>
High<br>

<span style="color:gold;">●</span>
Medium<br>

<span style="color:gray;">●</span>
Low
""",
"""
<b>Investment Priority</b><br>

<span style="color:red;">●</span>
P1 Immediate<br>

<span style="color:orange;">●</span>
P2 High Value<br>

<span style="color:gold;">●</span>
P3 Candidate<br>

<span style="color:gray;">●</span>
Monitor
"""
)


p.write_text(text)

print("Dashboard updated to priority levels")

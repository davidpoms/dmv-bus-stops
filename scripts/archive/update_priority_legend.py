from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

old = """
        <b>Impact Level</b><br>

        <span style="color:red;">●</span>
        Very High<br>

        <span style="color:orange;">●</span>
        High<br>

        <span style="color:gold;">●</span>
        Medium<br>

        <span style="color:gray;">●</span>
        Low
"""

new = """
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

if old in text:
    text = text.replace(old, new, 1)
    p.write_text(text)
    print("Updated legend")
else:
    print("Legend block not found")

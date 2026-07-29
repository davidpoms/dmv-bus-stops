from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

old = """
        <b>Community Action Status</b><br>

        <span style="color:gray;">●</span>
        Needs community review<br>

        <span style="color:orange;">●</span>
        Community review underway<br>

        <span style="color:green;">●</span>
        Candidate for bench<br>

        <span style="color:blue;">●</span>
        Bench installed
"""

new = """
        <b>Community Evidence Status</b><br>

        <span style="color:gray;">●</span>
        Needs community review<br>

        <span style="color:orange;">●</span>
        Evidence being gathered<br>

        <span style="color:green;">●</span>
        Validated candidate for action<br>

        <span style="color:blue;">●</span>
        Community project completed
"""


if old not in text:
    print("legend block not found")
    raise SystemExit(1)


text = text.replace(old, new)

p.write_text(text)

print("legend language updated")

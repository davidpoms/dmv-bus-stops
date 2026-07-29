from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()


old = """
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


new = """
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


if old not in text:
    print("legend block not found")
    raise SystemExit(1)


text = text.replace(
    old,
    new
)


p.write_text(text)

print("validation legend patched")


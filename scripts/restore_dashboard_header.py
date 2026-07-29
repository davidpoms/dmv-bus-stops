from pathlib import Path

p = Path("src/dashboard/templates/dashboard.html")

text = p.read_text()


# Replace old title block
old = """
<h1>
DMV Bus Stop Improvement Dashboard
</h1>
"""


new = """
<h1>
DMV Bus Stop Intelligence
</h1>


<div class="dashboard-links">

<a href="/handbook">
📘 Community Handbook
</a>


<a href="/volunteer-handbook">
🤝 Volunteer Handbook
</a>

</div>

"""


if old in text:
    text = text.replace(old, new)
    print("Restored dashboard title and handbook links")

else:
    print("Old title not found, checking existing title")

    start = text.find("<h1>")

    if start != -1:

        end = text.find("</h1>", start)

        if end != -1:

            end += len("</h1>")

            text = (
                text[:start]
                + new
                + text[end:]
            )

            print("Replaced existing h1 block")


p.write_text(text)

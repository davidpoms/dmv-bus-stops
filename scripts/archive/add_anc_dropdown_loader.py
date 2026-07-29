from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

if '"/geography/dc-ancs"' in text:
    print("ANC loader already exists")

else:

    marker = """
    fetch("/geography/counties")
"""

    addition = """
    fetch("/geography/dc-ancs")
    .then(r => r.json())
    .then(data => {

        populateSelect(
            "ancFilter",
            data
        );

    });


"""

    if marker not in text:
        raise Exception("Could not find county loader")

    text = text.replace(
        marker,
        addition + marker
    )

    p.write_text(text)

    print("Added ANC dropdown loader")

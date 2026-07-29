from pathlib import Path

p = Path("src/dashboard/static/review_stop.js")

text = p.read_text()

old = """
            const data =
                await response.json();
"""

new = """
            const data =
                await response.json();

            console.log(
                "Survey data:",
                data
            );
"""

if old not in text:
    raise Exception(
        "Could not find survey JSON block"
    )

text = text.replace(
    old,
    new
)

p.write_text(text)

print(
    "Added review stop debug logging"
)

from pathlib import Path

p = Path("src/dashboard/static/review_survey.js")

text = p.read_text()

old = """
        const container =
            document.getElementById(
                "stopInfo"
            );
"""

new = """
        const container = null;
"""

if old not in text:
    raise Exception(
        "Could not find stopInfo container block"
    )

text = text.replace(old,new,1)

old2 = """
        container.innerHTML =
"""

if old2 in text:
    text = text.replace(
        old2,
        """
        // disabled stopInfo overwrite
        /*
        container.innerHTML =
        """,
        1
    )

p.write_text(text)

print(
    "Disabled review_survey stopInfo overwrite"
)

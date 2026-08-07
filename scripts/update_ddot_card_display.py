from pathlib import Path

path = Path("src/dashboard/static/stop_detail.js")

text = path.read_text(encoding="utf-8")


old = """
                    <strong>
                    ${item.source}
                    </strong>
"""


new = """
                    <strong>
                    ${item.public_status || item.source}
                    </strong>
"""


if old not in text:
    raise SystemExit(
        "Could not find DDOT source heading"
    )


text = text.replace(
    old,
    new,
    1
)


old_source = """
                    ${item.finding}

                    <br>

                    Confidence:
"""


new_source = """
                    ${item.finding}

                    <br><br>

                    Evidence source:

                    <strong>
                    ${item.source}
                    </strong>

                    <br>

                    Confidence:
"""


if old_source not in text:
    raise SystemExit(
        "Could not find DDOT evidence source section"
    )


text = text.replace(
    old_source,
    new_source,
    1
)


path.write_text(
    text,
    encoding="utf-8"
)


print(
    "Updated DDOT stop card display"
)
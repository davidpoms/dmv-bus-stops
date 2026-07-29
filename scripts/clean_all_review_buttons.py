from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()


start_marker = """
                                popup += `

                                <br><br>

                                <a
                                href="/review/start?stop_id=${props.stop_id}"
                                class="stop-review-button">
                                Review this stop
                                </a>

                                `;
"""


start = text.find(start_marker)

if start == -1:
    raise Exception(
        "Could not find first review button block"
    )


end = text.find(
    """
                                marker.bindPopup(
                                    popup
                                ).openPopup();
""",
    start
)


if end == -1:
    raise Exception(
        "Could not find popup binding"
    )


replacement = """
                                popup += `

                                <br><br>

                                <a
                                href="/review/start?stop_id=${props.stop_id}"
                                class="stop-review-button">
                                Review this stop
                                </a>

                                `;


"""


text = (
    text[:start]
    +
    replacement
    +
    text[end:]
)


p.write_text(text)

print(
    "Cleaned duplicate review buttons"
)

from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()


start = text.find("popup += `")

while start != -1:

    end = text.find("`;", start)

    if end == -1:
        break

    block = text[start:end]

    if "Review this stop" in block:

        text = (
            text[:start]
            +
            text[end+2:]
        )

        break

    start = text.find(
        "popup += `",
        end
    )


marker = """
                                marker.bindPopup(
                                    popup
                                ).openPopup();
"""


insert = """
                                popup += `

                                <br><br>

                                <a
                                href="/review/start?stop_id=${props.stop_id}"
                                class="stop-review-button">
                                Review this stop
                                </a>

                                `;


                                marker.bindPopup(
                                    popup
                                ).openPopup();
"""


if marker not in text:
    raise Exception(
        "Popup binding not found"
    )


text = text.replace(
    marker,
    insert,
    1
)


p.write_text(text)

print(
    "Cleaned review button duplicates"
)

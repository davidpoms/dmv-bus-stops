from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

button_start = "popup += `"
button_text = "Review this stop"

count = 0

while True:

    start = text.find(button_start)

    if start == -1:
        break

    end = text.find("`;", start)

    if end == -1:
        break

    block = text[start:end]

    if button_text in block:

        text = (
            text[:start]
            +
            text[end+2:]
        )

        count += 1

    else:

        text = (
            text[:start+len(button_start)]
            +
            text[start+len(button_start):]
        )

        break


marker = """
                                marker.bindPopup(
                                    popup
                                ).openPopup();
"""


button = """
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
    raise Exception("Could not find popup binding")


text = text.replace(
    marker,
    button,
    1
)


p.write_text(text)

print(
    f"Removed {count} duplicate buttons and added one clean button"
)

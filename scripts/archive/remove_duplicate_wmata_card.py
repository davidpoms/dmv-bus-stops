from pathlib import Path

p = Path("src/dashboard/static/review_info_loader.js")

text = p.read_text()

start_marker = """
                    ${
                        info.wmata
                        ?
                        `
                        <br><br>

                        <div class="evidence-card">

                            <strong>
                            WMATA Stop Inventory
"""

start = text.find(start_marker)

if start == -1:
    raise Exception(
        "Could not find duplicate WMATA card"
    )

end_marker = """
                        `
                        :
                        ""
                    }


                    ${
                        info.streetview_url
"""

end = text.find(end_marker, start)

if end == -1:
    raise Exception(
        "Could not find end of duplicate WMATA card"
    )

text = (
    text[:start]
    +
    "\n\n"
    +
    text[end:]
)

text = text.replace(
    "WMATA Transit Information",
    "Current Stop Amenities (WMATA)",
    1
)

p.write_text(text)

print("Removed duplicate WMATA card")

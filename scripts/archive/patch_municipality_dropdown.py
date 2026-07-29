from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()


old = """
        const county =
            this.value;


        loadStops(
            "",
            "",
            "",
            state,
            county
        );
"""


new = """
        const county =
            this.value;


        const municipality =
            document.getElementById(
                "municipalitySelect"
            );


        municipality.innerHTML =
            "<option value=''>All Municipalities</option>";


        if (county) {

            fetch(
                "/geography/municipalities?county="
                + encodeURIComponent(county)
            )

            .then(
                response => response.json()
            )

            .then(
                data => {

                    populateSelect(
                        "municipalitySelect",
                        data
                    );

                }
            );

        }


        loadStops(
            "",
            "",
            "",
            state,
            county
        );
"""


if old not in text:
    raise SystemExit(
        "County handler block not found"
    )


text = text.replace(
    old,
    new
)


p.write_text(text)

print(
    "Municipality dropdown cascade patched"
)

from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()


old = """
            const impactText =
                impactSelect && impactSelect.value
                ?
                impactSelect.options[
                    impactSelect.selectedIndex
                ].text
                :
                "All Impacts";


            status.innerText =
                "Showing: "
                + routeText
                + " | "
                + impactText
                + " | Stops: "
                + data.features.length;
"""


new = """
            const impactText =
                impactSelect && impactSelect.value
                ?
                impactSelect.options[
                    impactSelect.selectedIndex
                ].text
                :
                "All Impacts";


            const stateSelect =
                document.getElementById(
                    "stateSelect"
                );

            const countySelect =
                document.getElementById(
                    "countySelect"
                );

            const municipalitySelect =
                document.getElementById(
                    "municipalitySelect"
                );

            const wardSelect =
                document.getElementById(
                    "wardSelect"
                );


            const geography = [
                stateSelect?.value,
                countySelect?.value,
                municipalitySelect?.value,
                wardSelect?.value
            ]
            .filter(Boolean)
            .join(" > ");


            status.innerText =
                "Showing: "
                + routeText
                + " | "
                + impactText
                + " | "
                + (
                    geography
                    ?
                    geography
                    :
                    "All Geography"
                )
                + " | Stops: "
                + data.features.length;
"""


if old not in text:
    raise SystemExit(
        "Status block not found"
    )


text = text.replace(
    old,
    new
)


p.write_text(text)

print(
    "Dashboard filter status patched"
)

from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

js = p.read_text()


old = """        console.log(
            "Features returned:",
            data.features.length
        );

        data.features.forEach(
"""


new = """        console.log(
            "Features returned:",
            data.features.length
        );


        const status =
            document.getElementById("routeStatus");


        if (status) {

            const routeSelect =
                document.getElementById("routeSelect");


            const impactSelect =
                document.getElementById("impactSelect");


            const routeText =
                routeSelect.value
                ?
                routeSelect.options[
                    routeSelect.selectedIndex
                ].text
                :
                "All Routes";


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

        }


        data.features.forEach(
"""


if old not in js:
    raise SystemExit("Marker loading block not found")


js = js.replace(old, new, 1)


p.write_text(js)

print("Added stop count status")

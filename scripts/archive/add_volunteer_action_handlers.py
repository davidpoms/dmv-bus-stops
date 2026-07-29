from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()


insert = """

function loadVolunteerMode(mode) {


    if (mode === "opportunity") {

        loadStops(
            "",
            "",
            "",
            "",
            "",
            "",
            ""
        );

        return;
    }


    if (mode === "route") {

        document
            .getElementById("routeSelect")
            .focus();

        return;
    }


    if (mode === "nearby") {

        alert(
            "Nearby review will use your location to find stops needing validation."
        );

        return;
    }

}

"""


text += insert


p.write_text(text)

print("volunteer handlers added")


from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()


insert_after = """
fetch("/routes")

.then(
    response => response.json()
)

.then(
    routes => {

        const select =
            document.getElementById("routeSelect");


        routes.forEach(
            route => {

                const option =
                    document.createElement("option");


                option.value =
                    route.route_id;


                option.text =
                    route.route_id +
                    " - " +
                    route.route_name;


                select.appendChild(
                    option
                );

            }
        );

    }
);
"""


addition = r"""


// ----------------------------
// Geography dropdown loading
// ----------------------------

function populateSelect(
    id,
    values
){

    const select =
        document.getElementById(id);

    if (!select) {
        return;
    }


    values.forEach(
        value => {

            const option =
                document.createElement("option");

            option.value = value;
            option.text = value;

            select.appendChild(option);

        }
    );

}


fetch("/geography/states")
.then(
    response => response.json()
)
.then(
    data => populateSelect(
        "stateSelect",
        data
    )
);



fetch("/geography/dc-wards")
.then(
    response => response.json()
)
.then(
    data => populateSelect(
        "wardSelect",
        data
    )
);



document
.getElementById("stateSelect")
.addEventListener(
    "change",
    function(){

        const state = this.value;

        const county =
            document.getElementById("countySelect");

        county.innerHTML =
            "<option value=''>All Counties</option>";


        if (!state) {
            loadStops();
            return;
        }


        fetch(
            "/geography/counties?state="
            + state
        )
        .then(
            response => response.json()
        )
        .then(
            data => {

                populateSelect(
                    "countySelect",
                    data
                );

                loadStops(
                    "",
                    "",
                    "",
                    state
                );

            }
        );

    }
);



document
.getElementById("countySelect")
.addEventListener(
    "change",
    function(){

        const state =
            document.getElementById(
                "stateSelect"
            ).value;


        const county =
            this.value;


        loadStops(
            "",
            "",
            "",
            state,
            county
        );

    }
);



document
.getElementById("municipalitySelect")
.addEventListener(
    "change",
    function(){

        const state =
            document.getElementById(
                "stateSelect"
            ).value;


        const county =
            document.getElementById(
                "countySelect"
            ).value;


        loadStops(
            "",
            "",
            "",
            state,
            county,
            this.value
        );

    }
);



document
.getElementById("wardSelect")
.addEventListener(
    "change",
    function(){

        loadStops(
            "",
            "",
            "",
            "DC",
            "",
            "",
            this.value
        );

    }
);

"""

if addition.strip() not in text:

    if insert_after in text:
        text = text.replace(
            insert_after,
            insert_after + addition
        )
    else:
        raise SystemExit(
            "Route loader block not found"
        )

else:
    print("Dropdown loader already patched")


p.write_text(text)

print("Dashboard geography dropdown wiring complete")

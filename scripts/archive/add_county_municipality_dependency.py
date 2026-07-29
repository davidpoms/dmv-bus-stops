from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()


if "function loadMunicipalityFilters" in text:
    print("Municipality dependency already exists")
    exit()


marker = """
    loadRegionalGeography();


    document
    .getElementById("stateFilter")
"""

addition = r"""
    function loadMunicipalityFilters(){

        const state =
            document.getElementById(
                "stateFilter"
            )?.value || "";


        const county =
            document.getElementById(
                "countyFilter"
            )?.value || "";


        let url =
            "/geography/municipalities";


        const params =
            new URLSearchParams();


        if(state){
            params.append(
                "state",
                state
            );
        }


        if(county){
            params.append(
                "county",
                county
            );
        }


        if(params.toString()){

            url +=
                "?" +
                params.toString();

        }


        fetch(url)
        .then(r => r.json())
        .then(data => {

            populateSelect(
                "municipalityFilter",
                data
            );

        });

    }


    document
    .getElementById("countyFilter")
    ?.addEventListener(
        "change",
        loadMunicipalityFilters
    );


"""

if marker not in text:
    raise Exception("Could not find geography initialization block")


text = text.replace(
    marker,
    addition + marker
)


p.write_text(text)

print("Added county to municipality dependency")

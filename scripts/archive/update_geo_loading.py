from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

old = """
    fetch("/geography/counties")
    .then(r => r.json())
    .then(data => {

        populateSelect(
            "countyFilter",
            data
        );

    });


    fetch("/geography/municipalities")
    .then(r => r.json())
    .then(data => {

        populateSelect(
            "municipalityFilter",
            data
        );

    });
"""

new = """
    function loadRegionalGeography(){

        const state =
            document.getElementById(
                "stateFilter"
            )?.value || "";


        let countyUrl =
            "/geography/counties";


        let municipalityUrl =
            "/geography/municipalities";


        if(state){

            countyUrl +=
                "?state=" +
                encodeURIComponent(state);


            municipalityUrl +=
                "?state=" +
                encodeURIComponent(state);

        }


        fetch(countyUrl)
        .then(r => r.json())
        .then(data => {

            populateSelect(
                "countyFilter",
                data
            );

        });


        fetch(municipalityUrl)
        .then(r => r.json())
        .then(data => {

            populateSelect(
                "municipalityFilter",
                data
            );

        });

    }


    loadRegionalGeography();


    document
    .getElementById("stateFilter")
    ?.addEventListener(
        "change",
        loadRegionalGeography
    );
"""

if old not in text:
    raise Exception("Could not find geography loading block")

text=text.replace(old,new)

p.write_text(text)

print("Updated dependent geography loading")

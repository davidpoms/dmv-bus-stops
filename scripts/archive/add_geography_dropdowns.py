from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

addition = r"""



function populateSelect(id, items){

    const select =
        document.getElementById(id);

    if(!select){
        return;
    }


    select.innerHTML =
        '<option value="">All</option>';


    items.forEach(
        item => {

            const option =
                document.createElement("option");

            option.value = item;
            option.textContent = item;

            select.appendChild(option);

        }
    );

}



function loadGeographyFilters(){

    fetch("/geography/states")
    .then(r => r.json())
    .then(data => {

        populateSelect(
            "stateFilter",
            data
        );

    });


    fetch("/geography/dc-wards")
    .then(r => r.json())
    .then(data => {

        populateSelect(
            "wardFilter",
            data
        );

    });


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


}



loadGeographyFilters();

"""

if "function loadGeographyFilters" in text:
    print("Geography loader already exists")
else:
    text += addition
    p.write_text(text)

    print("Geography dropdown loader added")

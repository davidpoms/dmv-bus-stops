from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

addition = r"""


function toggleGeoFilters(){

    const state =
        document.getElementById(
            "stateFilter"
        )?.value || "";


    const county =
        document.getElementById(
            "countyFilter"
        )?.closest("label");


    const municipality =
        document.getElementById(
            "municipalityFilter"
        )?.closest("label");


    const ward =
        document.getElementById(
            "wardFilter"
        )?.closest("label");


    const anc =
        document.getElementById(
            "ancFilter"
        )?.closest("label");


    if(!county || !municipality || !ward || !anc){
        return;
    }


    if(state === "DC"){

        county.style.display = "none";
        municipality.style.display = "none";

        ward.style.display = "flex";
        anc.style.display = "flex";

    }

    else if(
        state === "Maryland" ||
        state === "Virginia"
    ){

        county.style.display = "flex";
        municipality.style.display = "flex";

        ward.style.display = "none";
        anc.style.display = "none";

    }

    else {

        county.style.display = "flex";
        municipality.style.display = "flex";

        ward.style.display = "flex";
        anc.style.display = "flex";

    }

}



const stateFilter =
    document.getElementById(
        "stateFilter"
    );


if(stateFilter){

    stateFilter.addEventListener(
        "change",
        toggleGeoFilters
    );

}


window.addEventListener(
    "load",
    toggleGeoFilters
);

"""

if "function toggleGeoFilters" in text:
    print("Dependent geography filters already exist")

else:
    text += addition
    p.write_text(text)
    print("Dependent geography filters added")

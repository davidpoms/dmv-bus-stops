from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

start = text.find("function toggleGeoFilters(){")
end = text.find("\n\n\nconst stateFilter", start)

if start == -1 or end == -1:
    raise Exception("Could not find toggleGeoFilters block")


new = r"""
function toggleGeoFilters(){

    const state =
        document.getElementById(
            "stateFilter"
        )?.value || "";


    const normalized =
        state.toLowerCase();


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


    const isDC =
        normalized.includes("dc")
        ||
        normalized.includes("district");


    const isRegional =
        normalized.includes("maryland")
        ||
        normalized.includes("virginia")
        ||
        normalized.includes("md")
        ||
        normalized.includes("va");


    if(isDC){

        county.style.display = "none";
        municipality.style.display = "none";

        ward.style.display = "flex";
        anc.style.display = "flex";

    }


    else if(isRegional){

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

"""

text = text[:start] + new + text[end:]

p.write_text(text)

print("Hardened geography visibility")

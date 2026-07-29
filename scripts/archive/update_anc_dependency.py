from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()


start = text.find('fetch("/geography/dc-ancs")')

end = text.find('fetch("/geography/counties")', start)


if start == -1 or end == -1:
    raise Exception("Could not find ANC loader")


new = r'''
function loadAncFilters(){

    const ward =
        document.getElementById(
            "wardFilter"
        )?.value || "";


    let url =
        "/geography/dc-ancs";


    if(ward){

        url +=
            "?dc_ward=" +
            encodeURIComponent(ward);

    }


    fetch(url)
    .then(r => r.json())
    .then(data => {

        populateSelect(
            "ancFilter",
            data
        );

    });

}



loadAncFilters();



document
.getElementById("wardFilter")
?.addEventListener(
    "change",
    loadAncFilters
);



'''

text = text[:start] + new + text[end:]

p.write_text(text)

print("ANC dependency updated")

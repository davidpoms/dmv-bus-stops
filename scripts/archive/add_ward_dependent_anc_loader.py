from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

if "function loadAncFilters" in text:
    print("ANC dependency already exists")
    exit()


marker = """
    fetch("/geography/counties")
"""


addition = r"""
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


"""


if marker not in text:
    raise Exception("Could not find county loader")


text = text.replace(
    marker,
    addition + marker
)


p.write_text(text)

print("Added ward-dependent ANC loader")

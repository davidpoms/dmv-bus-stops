from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()


old = """
    fetch("/geography/dc-ancs")
    .then(r => r.json())
    .then(data => {

        populateSelect(
            "ancFilter",
            data
        );

    });

"""

new = r"""
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


if old not in text:
    raise Exception("Could not find ANC loader block")


text = text.replace(
    old,
    new
)


p.write_text(text)

print("ANC now depends on ward")

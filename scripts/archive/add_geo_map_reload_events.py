from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

if "geoMapFiltersConnected" in text:
    print("Already connected")
    exit()


marker = """
window.addEventListener(
    "load",
    toggleGeoFilters
);
"""

addition = r"""


// geoMapFiltersConnected

[
    "stateFilter",
    "countyFilter",
    "municipalityFilter",
    "wardFilter",
    "ancFilter"
].forEach(
    id => {

        const filter =
            document.getElementById(id);


        if(filter){

            filter.addEventListener(
                "change",
                function(){

                    loadStops();

                }
            );

        }

    }
);

"""

if marker not in text:
    raise Exception("Could not find load listener block")


text = text.replace(
    marker,
    marker + addition
)


p.write_text(text)

print("Connected geography changes to map reload")

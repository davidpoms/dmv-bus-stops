from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()


old = """
    [
        "review",
        "state",
        "county",
        "municipality",
        "dc_ward",
        "impact",
        "priority",
        "action"
    ].forEach(
"""


new = """
    [
        "review",
        "state",
        "county",
        "municipality",
        "dc_ward",
        "impact",
        "priority",
        "action"
    ].forEach(
"""


# Keep existing block; insert dropdown capture after it
marker = """
    if(params.toString()){

        url +=
            "?" +
            params.toString();

    }
"""

addition = r"""

    const geoFilters = {

        state:
            document.getElementById(
                "stateFilter"
            )?.value,

        county:
            document.getElementById(
                "countyFilter"
            )?.value,

        municipality:
            document.getElementById(
                "municipalityFilter"
            )?.value,

        dc_ward:
            document.getElementById(
                "wardFilter"
            )?.value,

        dc_anc:
            document.getElementById(
                "ancFilter"
            )?.value

    };


    Object.entries(geoFilters)
    .forEach(
        ([key,value]) => {

            if(value){

                params.append(
                    key,
                    value
                );

            }

        }
    );


    if(params.toString()){

        url =
            "/map/stops?" +
            params.toString();

    }
"""


if marker not in text:
    raise Exception("Could not find URL assembly block")


text = text.replace(
    marker,
    addition
)


p.write_text(text)

print("Connected geography filters to map")

from pathlib import Path

p = Path("src/dashboard/static/dashboard.js")

text = p.read_text()

old = """
    let url = "/map/stops";


    if (route) {
        url += "?route=" + route;
    }
"""

new = """
    let url = "/map/stops";


    const params = new URLSearchParams();


    if (route) {
        params.append(
            "route",
            route
        );
    }


    const pageParams =
        new URLSearchParams(
            window.location.search
        );


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
        key => {

            const value =
                pageParams.get(key);

            if(value){

                params.append(
                    key,
                    value
                );

            }

        }
    );


    if(params.toString()){

        url +=
            "?" +
            params.toString();

    }
"""

if old not in text:
    raise Exception("Could not find URL block")

text = text.replace(old, new)

p.write_text(text)

print("Map query filters added")

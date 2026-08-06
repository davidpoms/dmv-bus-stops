from pathlib import Path


JS = Path("src/dashboard/static/dashboard.js")


text = JS.read_text(encoding="utf-8")


old_start = "function loadStops(route=\"\") {"

start = text.find(old_start)

if start == -1:
    raise Exception("Could not find loadStops function")


# Find the section before marker creation
end_marker = "    fetch(url)"

end = text.find(end_marker, start)

if end == -1:
    raise Exception("Could not find end of loadStops setup section")


replacement = r'''function loadStops() {


    markers.forEach(
        marker => map.removeLayer(marker)
    );


    markers = [];


    let url =
        "/map/stops";


    const params =
        new URLSearchParams();



    const filters = {

        route:
            document.getElementById(
                "routeFilter"
            )?.value,


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
            )?.value,


        impact:
            document.getElementById(
                "impactFilter"
            )?.value,


        priority:
            document.getElementById(
                "priorityFilter"
            )?.value

    };



    Object.entries(filters)
    .forEach(
        ([key,value]) => {

            if(value && value !== "all"){

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



'''


text = (
    text[:start]
    +
    replacement
    +
    text[end:]
)


# Replace old route listener

old_listener = """routeFilter.addEventListener(
        "change",
        function(){

            loadStops(
                this.value
            );

        }
    );"""


new_listener = """routeFilter.addEventListener(
        "change",
        function(){

            loadStops();

        }
    );"""


if old_listener in text:

    text = text.replace(
        old_listener,
        new_listener
    )

else:
    print("Route listener already changed or not found")


JS.write_text(
    text,
    encoding="utf-8"
)


print(
    "Unified map filter integration complete."
)
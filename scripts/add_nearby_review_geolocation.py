from pathlib import Path


# ----------------------------
# Patch dashboard.html
# ----------------------------

html_path = Path(
    "src/dashboard/templates/dashboard.html"
)

html = html_path.read_text(
    encoding="utf-8"
)

old_html = """
<a href="/review/start?mode=nearby">
📍 Near Me
</a>
"""

new_html = """
<a href="#"
id="nearbyReviewLink">
📍 Near Me
</a>
"""

if old_html not in html:
    raise SystemExit(
        "Could not find Near Me link in dashboard.html"
    )

html = html.replace(
    old_html,
    new_html
)

html_path.write_text(
    html,
    encoding="utf-8"
)


# ----------------------------
# Patch dashboard.js
# ----------------------------

js_path = Path(
    "src/dashboard/static/dashboard.js"
)

js = js_path.read_text(
    encoding="utf-8"
)

marker = """
window.addEventListener(
    "load",
    loadRouteFilter
);
"""

addition = """

function enableNearbyReview(){

    const link =
        document.getElementById(
            "nearbyReviewLink"
        );


    if(!link){
        return;
    }


    link.addEventListener(
        "click",
        function(event){

            event.preventDefault();


            if(!navigator.geolocation){

                alert(
                    "Location services are not available."
                );

                return;
            }


            navigator.geolocation.getCurrentPosition(

                function(position){

                    const lat =
                        position.coords.latitude;

                    const lon =
                        position.coords.longitude;


                    window.location.href =
                        `/review/start?mode=nearby`
                        + `&lat=${lat}`
                        + `&lon=${lon}`;

                },


                function(){

                    alert(
                        "Unable to get your location. Please allow location access."
                    );

                }

            );

        }
    );

}


window.addEventListener(
    "load",
    enableNearbyReview
);

"""

if "enableNearbyReview" not in js:

    if marker not in js:
        raise SystemExit(
            "Could not find dashboard.js loadRouteFilter marker"
        )

    js = js.replace(
        marker,
        marker + addition
    )

    js_path.write_text(
        js,
        encoding="utf-8"
    )


print(
    "Added Near Me geolocation support"
)
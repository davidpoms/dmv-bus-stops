const map = L.map(
    'map'
).setView(
    [38.9072, -77.0369],
    11
);


map.createPane(
    "highPriority"
);

map.getPane(
    "highPriority"
).style.zIndex = 650;


map.createPane(
    "veryHighPriority"
);

map.getPane(
    "veryHighPriority"
).style.zIndex = 700;


L.tileLayer(
    'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
    {
        attribution:
        '&copy; OpenStreetMap contributors'
    }
).addTo(map);



let markers = [];


function loadStops(route="") {


    markers.forEach(
        marker => map.removeLayer(marker)
    );


    markers = [];

    console.log("Loading route:", route);


    let url = "/map/stops";


    if (route) {
        url += "?route=" + route;
    }


    fetch(url)

    .then(
        response => response.json()
    )

    .then(
        data => {

        console.log(
            "Features returned:",
            data.features.length
        );

        data.features.forEach(
            feature => {

                const coords =
                    feature.geometry.coordinates;


                const props =
                    feature.properties;


                let color = "gray";
                let radius = 5;


                if (
                    props.impact === "very_high"
                ) {
                    color = "red";
                    radius = 14;
                }

                else if (
                    props.impact === "high"
                ) {
                    color = "orange";
                    radius = 10;
                }

                else if (
                    props.impact === "medium"
                ) {
                    color = "gold";
                    radius = 7;
                }


                const marker = L.circleMarker(
                    [
                        coords[1],
                        coords[0]
                    ],
                    {
                        radius:radius,
                        color:color,
                        fillOpacity:0.7,

                        pane:
                            props.impact === "very_high"
                            ? "veryHighPriority"
                            :
                            props.impact === "high"
                            ? "highPriority"
                            :
                            "markerPane"
                    }
                )
                .addTo(map);


                markers.push(marker);

                console.log(
                    "Markers on map:",
                    markers.length
                );


                if (
                    props.impact === "very_high" ||
                    props.impact === "high"
                ) {

                    marker.bringToFront();

                }


                marker.on(
                    "click",
                    function() {

                        fetch(
                            `/stops/${props.stop_id}`
                        )

                        .then(
                            response => response.json()
                        )

                        .then(
                            detail => {

                                let popup = `
                                <b>${props.location}</b><br><br>

                                Score: ${props.score}<br>
                                Impact: ${props.impact}<br><br>

                                <b>Projects</b><br>
                                `;


                                if (detail.projects.length > 0) {

                                    detail.projects.forEach(
                                        project => {

                                            popup +=
                                            `${project.recommendation}: ${project.status}<br>`;

                                        }
                                    );

                                }

                                else {

                                    popup +=
                                    "No active projects<br>";

                                }


                                if (
                                    detail.projects.length === 0
                                ) {

                                    popup += `
                                    <br>
                                    <button
                                        class="adoptStopButton"
                                        data-stop="${props.stop_id}">
                                        Adopt this stop
                                    </button>
                                    `;

                                }


                                if (detail.confidence) {

                                    popup += `
                                    <br>
                                    <b>Evidence</b><br>

                                    Status:
                                    ${detail.confidence[0]}<br>

                                    Confidence:
                                    ${detail.confidence[1]}<br>
                                    `;


                                    if (
                                        detail.confidence[0] === "unreviewed"
                                    ) {

                                        popup += `
                                        <br>
                                        <b>Recommended action:</b><br>
                                        Field review needed
                                        `;

                                    }

                                    else {

                                        popup += `
                                        <br>
                                        <b>Recommended action:</b><br>
                                        Implementation review
                                        `;

                                    }

                                }


                                if (detail.review) {

                                    popup += `
                                    <br>
                                    <b>Field Review</b><br>

                                    Reviewer:
                                    ${detail.review[0]}<br>

                                    Notes:
                                    ${detail.review[6]}<br>
                                    `;

                                }


                                marker.bindPopup(
                                    popup
                                ).openPopup();

                            }
                        );

                    }
                );

            }
        );

    }
);

}

fetch("/routes")

.then(
    response => response.json()
)

.then(
    routes => {

        const select =
            document.getElementById("routeSelect");


        routes.forEach(
            route => {

                const option =
                    document.createElement("option");


                option.value =
                    route.route_id;


                option.text =
                    route.route_id +
                    " - " +
                    route.route_name;


                select.appendChild(
                    option
                );

            }
        );

    }
);



document
.getElementById("routeSelect")
.addEventListener(
    "change",
    function() {

        loadStops(
            this.value
        );

    }
);



loadStops();


document.addEventListener(
    "click",
    function(event) {

        if (
            event.target.classList.contains(
                "adoptStopButton"
            )
        ) {

            const stopId =
                event.target.dataset.stop;


            fetch(
                `/stops/${stopId}/community-action`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                        "application/json"
                    },

                    body: JSON.stringify(
                        {
                            status: "planned",
                            project_type:
                                "community_review",
                            steward:
                                "Dashboard Volunteer",
                            notes:
                                "Adopted through dashboard"
                        }
                    )
                }
            )
            .then(
                response => response.json()
            )
            .then(
                data => {

                    alert(
                        "Stop adopted!"
                    );

                    location.reload();

                }
            );

        }

    }
);

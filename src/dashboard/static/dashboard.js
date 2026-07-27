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


function loadEvidence(stopId) {

    return fetch(
        `/api/stops/${stopId}/evidence`
    )
    .then(
        response => response.json()
    );

}



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

                                return loadEvidence(props.stop_id)
                                .then(
                                    evidence => {

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


                                if (evidence.osm) {

                                    popup += `
                                    <br>
                                    <b>OSM Evidence</b><br>

                                    Bus stop mapped:
                                    ${evidence.osm.osm_bus_stop === 1 ? "Yes" : "No"}<br>

                                    Shelter:
                                    ${evidence.osm.osm_shelter === 1 ? "Yes" : "No"}<br>

                                    Bench:
                                    ${evidence.osm.osm_bench === 1 ? "Yes" : "No"}<br>
                                    `;

                                }


                                if (evidence.observations.length > 0) {

                                    popup += `
                                    <br>
                                    <b>Field Observations</b><br>
                                    `;


                                    evidence.observations.forEach(
                                        obs => {

                                            popup += `
                                            Reviewer:
                                            ${obs.observer || "Unknown"}<br>

                                            Bench:
                                            ${obs.bench_present}<br>

                                            Feasible:
                                            ${obs.bench_feasible}<br>

                                            Confidence:
                                            ${obs.confidence}<br>

                                            Notes:
                                            ${obs.notes || ""}<br><br>
                                            `;

                                        }
                                    );

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


// -------------------------------
// Review queue loader
// -------------------------------

function loadReviewQueue(){

    fetch("/api/review-queue")
    .then(r => r.json())
    .then(data => {

        const container =
            document.getElementById("reviewQueue");

        if (!container){
            console.log(
                "reviewQueue container missing"
            );
            return;
        }


        container.innerHTML = "";


        data.queue.forEach(stop => {

            container.innerHTML += `

            <div class="review-card">

                <h4>
                ${stop.location_name || "Bus Stop"}
                </h4>

                <p>
                Priority:
                ${stop.priority}
                </p>

                <p>
                Opportunity:
                ${stop.evidence.opportunity_score}
                </p>

                <button
                onclick="window.location='/survey-page/${stop.stop_id}'">
                Review Stop
                </button>

            </div>

            `;

        });

    });

}


document.addEventListener(
"DOMContentLoaded",
function(){

    if(
        document.getElementById(
            "reviewQueue"
        )
    ){
        loadReviewQueue();
    }

});



// -----------------------------
// Pipeline table
// -----------------------------

let pipelineData = [];


function loadPipeline(){

    fetch("/pipeline/geography")
    .then(r => r.json())
    .then(data => {

        pipelineData = data;

        renderPipeline(data);

    });

}


function renderPipeline(rows){

    const body =
        document.getElementById("pipelineBody");


    body.innerHTML = "";


    rows.forEach(row => {

        body.innerHTML += `

        <tr>

        <td>${row.type}</td>

        <td>${row.geography}</td>

        <td>${row.stops}</td>

        <td>${row.queued}</td>

        <td>${row.assigned}</td>

        <td>${row.reviewed}</td>

        <td>${row.consensus}</td>

        <td>

        <progress
        value="${row.completion_pct}"
        max="100">
        </progress>

        ${row.completion_pct}%

        </td>

        </tr>

        `;

    });

}



function filterPipeline(type){

    if(type===""){

        renderPipeline(pipelineData);
        return;

    }


    renderPipeline(
        pipelineData.filter(
            x => x.type === type
        )
    );

}



function searchPipeline(){

    let q =
        document
        .getElementById("pipelineSearch")
        .value
        .toLowerCase();


    renderPipeline(

        pipelineData.filter(
            x =>
            x.geography
            .toLowerCase()
            .includes(q)
        )

    );

}


// -----------------------------
// Review Queue
// -----------------------------

function loadReviewQueue(){

    fetch("/api/review-queue")

    .then(r=>r.json())

    .then(data=>{


        let div =
        document.getElementById(
            "reviewQueue"
        );


        div.innerHTML = "";


        data.queue.forEach(item=>{

            div.innerHTML += `

            <div class="review-card">

            <b>
            ${item.type}
            </b>

            <br>

            Stop:
            ${item.stop_id}

            <br>

            Score:
            ${item.evidence.opportunity_score}

            <br>

            ${item.reasons.join("<br>")}

            <br>

            <a href="/stops/${item.stop_id}">
            Open stop
            </a>

            </div>

            `;

        });


    });

}



document.addEventListener(
"DOMContentLoaded",
()=>{

    loadPipeline();

    loadReviewQueue();


    const params =
        new URLSearchParams(
            window.location.search
        );


    if(params.get("review")){

        console.log(
            "Review mode:",
            params.get("review")
        );

    }

});



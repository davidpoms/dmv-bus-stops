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
        `/stops/${stopId}`
    )
    .then(
        response => {

            if(!response.ok){

                return {
                    osm: {},
                    observations: []
                };

            }

            return response.json();

        }
    )
    .then(
        data => {

            return {

                osm:
                    data.evidence?.osm || {},

                observations:
                    data.evidence?.reviews || [],

                wmata_history:
                    data.wmata_history || [],

                wmata_evidence:
                    data.wmata_evidence || null

            };

        }
    )
    .catch(
        error => {

            console.warn(
                "Evidence unavailable:",
                error
            );

            return {
                osm: {},
                observations: []
            };

        }
    );

}



function loadStops(route="") {


    markers.forEach(
        marker => map.removeLayer(marker)
    );


    markers = [];

    console.log("Loading route:", route);


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

                        Promise.all([
                            fetch(`/stops/${props.stop_id}`)
                                .then(response => response.json()),

                            fetch(`/stops/${props.stop_id}/amenities`)
                                .then(response => {
                                    if (!response.ok) {
                                        return {
                                            wmata: null,
                                            osm: null
                                        };
                                    }

                                    return response.json();
                                })
                        ])

                        .then(
                            ([detail, amenities]) => {

                                detail.amenities = amenities;

                                const evidence = {

                                    osm:
                                        detail.evidence?.osm || {},

                                    observations:
                                        detail.evidence?.reviews || [],

                                    wmata_evidence:
                                        detail.wmata_evidence || null

                                };


                                let reviewReason =
                                    "This stop has been identified as a possible opportunity for improvement. Community feedback will help determine whether riders would benefit from changes like seating, shelter, or other waiting area improvements.";


                                if (
                                    evidence.observations &&
                                    evidence.observations.length > 0
                                ) {

                                    reviewReason =
                                        "Community members have already provided feedback about this stop. Additional observations help confirm improvement needs.";

                                }


                                else if (
                                    evidence.osm &&
                                    evidence.osm.osm_shelter === 1 &&
                                    evidence.osm.osm_bench === 0
                                ) {

                                    reviewReason =
                                        "This stop appears to have a shelter, but seating information needs verification. Your review will help confirm whether riders have a place to sit while waiting.";

                                }


                                else if (
                                    detail.amenities?.wmata?.shelter === "1"
                                ) {

                                    reviewReason =
                                        "Available records indicate this stop has a shelter, but seating information or rider experience may need verification.";

                                }


                                else if (
                                    detail.amenities?.wmata?.shelter !== "1" &&
                                    evidence.osm &&
                                    evidence.osm.osm_shelter === 0 &&
                                    evidence.osm.osm_bench === 0
                                ) {

                                    reviewReason =
                                        "Available records do not show a shelter or bench. Your review will help determine whether riders would benefit from improved waiting conditions.";

                                }



                                let popup = `
                                <b>${props.location.replace("+", " at ")}</b><br><br>

                                <b>Why this stop is being reviewed</b><br>

                                ${reviewReason}
                                <br><br>

                                <b>Current improvement projects</b><br>
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
                                    "No active improvement projects<br>";

                                }


                                if (
                                    detail.projects.length === 0
                                ) {

                                    popup += `
                                    <br>
                                    <button
                                        class="adoptStopButton"
                                        data-stop="${props.stop_id}">
                                        Become a community steward
                                    </button>
                                    `;

                                }


                                if (
                                    evidence.osm ||
                                    detail.amenities?.wmata
                                ) {

                                    popup += `
                                    <br>
                                    <b>Existing stop information</b><br>
                                    `;


                                    if (detail.amenities?.wmata) {

                                        popup += `
                                        Shelter:
                                        ${
                                            detail.amenities.wmata.shelter === "1"
                                            ? "Yes"
                                            : "No"
                                        }
                                        (WMATA inventory)<br>

                                        Bench:
                                        ${
                                            detail.amenities.wmata.bench === "1"
                                            ? "Yes"
                                            : "No"
                                        }
                                        (WMATA inventory)<br>

                                        Accessible boarding:
                                        ${
                                            detail.amenities.wmata.accessible === "Y"
                                            ? "Yes"
                                            : "No"
                                        }<br>
                                        `;

                                    }


                                    if (evidence.osm) {

                                        popup += `
                                        Public mapping evidence:<br>

                                        Shelter mapped:
                                        ${
                                            evidence.osm.osm_shelter === 1
                                            ? "Yes"
                                            : "No"
                                        }<br>

                                        Bench mapped:
                                        ${
                                            evidence.osm.osm_bench === 1
                                            ? "Yes"
                                            : "No"
                                        }<br>
                                        `;

                                    }

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

                                            Field observation - bench present:
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


                                


                                popup += `

                                <br><br>

                                <a
                                href="/review/start?stop_id=${props.stop_id}"
                                class="stop-review-button">
                                Review this stop
                                </a>

                                `;



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



const routeSelect = document.getElementById("routeSelect");

if(routeSelect){

    routeSelect.addEventListener(
        "change",
        function(){

            loadStops(
                this.value
            );

        }
    );

}



if(document.getElementById("map")){
    loadStops();
}


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


// -----------------------------
// Pipeline table
// -----------------------------

let pipelineData = [];


function loadPipeline(){

    const body = document.getElementById("pipelineBody");

    if (!body) {
        console.warn("Pipeline section missing");
        return;
    }

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


    if(!body){
        console.warn("Pipeline body missing");
        return;
    }


    body.innerHTML="";


    rows.forEach(row=>{

        body.innerHTML += `

<tr>

<td>${row.type}</td>

<td>${row.geography}</td>

<td>${row.stops}</td>

<td>${row.queued}</td>

<td>${row.reviewed}</td>

<td>${row.consensus}</td>

<td>
${row.wmata_evidence || 0}
</td>

<td>
${row.osm?.mapped_benches || 0}
</td>

<td>
${row.osm?.mapped_shelters || 0}
</td>

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


function loadEvidenceSummary(){

    fetch("/api/evidence-summary")
    .then(r => r.json())
    .then(data => {

        const shelter =
            document.getElementById(
                "likelyShelter"
            );

        const bench =
            document.getElementById(
                "likelyBench"
            );

        const none =
            document.getElementById(
                "noShelterEvidence"
            );


        if (shelter){
            shelter.textContent =
                data.likely_shelter;
        }

        if (bench){
            bench.textContent =
                data.likely_bench;
        }

        if (none){
            none.textContent =
                data.no_shelter_evidence;
        }

    });

}


document.addEventListener(
"DOMContentLoaded",
()=>{

    loadEvidenceSummary();

});


document.addEventListener(
    "DOMContentLoaded",
    function(){

        loadPipeline();

    }
);





const applyMapFilters =
    document.getElementById(
        "applyMapFilters"
    );


if(applyMapFilters){

    applyMapFilters.addEventListener(
        "click",
        function(){

            const state =
                document.getElementById(
                    "stateFilter"
                )?.value || "";


            const county =
                document.getElementById(
                    "countyFilter"
                )?.value || "";


            const ward =
                document.getElementById(
                    "wardFilter"
                )?.value || "";


            const params =
                new URLSearchParams();


            if(state){
                params.append(
                    "state",
                    state
                );
            }


            if(county){
                params.append(
                    "county",
                    county
                );
            }


            if(ward){
                params.append(
                    "dc_ward",
                    ward
                );
            }


            const url =
                "/dashboard?" +
                params.toString();


            window.location.href = url;

        }
    );

}





function populateSelect(id, items){

    const select =
        document.getElementById(id);

    if(!select){
        return;
    }


    select.innerHTML =
        '<option value="">All</option>';


    items.forEach(
        item => {

            const option =
                document.createElement("option");

            option.value = item;
            option.textContent = item;

            select.appendChild(option);

        }
    );

}



function loadGeographyFilters(){

    fetch("/geography/states")
    .then(r => r.json())
    .then(data => {

        populateSelect(
            "stateFilter",
            data
        );

    });


    fetch("/geography/dc-wards")
    .then(r => r.json())
    .then(data => {

        populateSelect(
            "wardFilter",
            data
        );

    });


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



    function loadRegionalGeography(){

        const state =
            document.getElementById(
                "stateFilter"
            )?.value || "";


        let countyUrl =
            "/geography/counties";


        let municipalityUrl =
            "/geography/municipalities";


        if(state){

            countyUrl +=
                "?state=" +
                encodeURIComponent(state);


            municipalityUrl +=
                "?state=" +
                encodeURIComponent(state);

        }


        fetch(countyUrl)
        .then(r => r.json())
        .then(data => {

            populateSelect(
                "countyFilter",
                data
            );

        });


        fetch(municipalityUrl)
        .then(r => r.json())
        .then(data => {

            populateSelect(
                "municipalityFilter",
                data
            );

        });

    }


    function loadMunicipalityFilters(){

        const state =
            document.getElementById(
                "stateFilter"
            )?.value || "";


        const county =
            document.getElementById(
                "countyFilter"
            )?.value || "";


        let url =
            "/geography/municipalities";


        const params =
            new URLSearchParams();


        if(state){
            params.append(
                "state",
                state
            );
        }


        if(county){
            params.append(
                "county",
                county
            );
        }


        if(params.toString()){

            url +=
                "?" +
                params.toString();

        }


        fetch(url)
        .then(r => r.json())
        .then(data => {

            populateSelect(
                "municipalityFilter",
                data
            );

        });

    }


    document
    .getElementById("countyFilter")
    ?.addEventListener(
        "change",
        loadMunicipalityFilters
    );



    loadRegionalGeography();


    document
    .getElementById("stateFilter")
    ?.addEventListener(
        "change",
        loadRegionalGeography
    );


}



loadGeographyFilters();





function toggleGeoFilters(){

    const state =
        document.getElementById(
            "stateFilter"
        )?.value || "";


    const normalized =
        state.toLowerCase();


    const county =
        document.getElementById(
            "countyFilter"
        )?.closest("label");


    const municipality =
        document.getElementById(
            "municipalityFilter"
        )?.closest("label");


    const ward =
        document.getElementById(
            "wardFilter"
        )?.closest("label");


    const anc =
        document.getElementById(
            "ancFilter"
        )?.closest("label");


    if(!county || !municipality || !ward || !anc){
        return;
    }


    const isDC =
        normalized.includes("dc")
        ||
        normalized.includes("district");


    const isRegional =
        normalized.includes("maryland")
        ||
        normalized.includes("virginia")
        ||
        normalized.includes("md")
        ||
        normalized.includes("va");


    if(isDC){

        county.style.display = "none";
        municipality.style.display = "none";

        ward.style.display = "flex";
        anc.style.display = "flex";

    }


    else if(isRegional){

        county.style.display = "flex";
        municipality.style.display = "flex";

        ward.style.display = "none";
        anc.style.display = "none";

    }


    else {

        county.style.display = "flex";
        municipality.style.display = "flex";

        ward.style.display = "flex";
        anc.style.display = "flex";

    }

}




const stateFilter =
    document.getElementById(
        "stateFilter"
    );


if(stateFilter){

    stateFilter.addEventListener(
        "change",
        toggleGeoFilters
    );

}


window.addEventListener(
    "load",
    toggleGeoFilters
);



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



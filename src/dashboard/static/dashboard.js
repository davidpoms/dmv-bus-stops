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



function loadStops() {


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
                let radius = 7;


                const marker = L.circleMarker(
                    [
                        coords[1],
                        coords[0]
                    ],
                    {
                        radius:radius,
                        color:color,
                        fillOpacity:0.7,

                        pane: "markerPane"
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

                        fetch(`/stops/${props.stop_id}`)
                        .then(response => response.json())

                        .then(
                            (detail) => {

                                detail.amenities = {
                                    wmata:
                                        detail.wmata_evidence
                                };

                                const evidence = {

                                    osm:
                                        detail.evidence?.osm || {},

                                    observations:
                                        detail.evidence?.reviews || [],

                                    wmata_evidence:
                                        detail.wmata_evidence || null

                                };


                                let reviewReason =
                                    "This stop has been prioritized for community verification because available information suggests additional review would be valuable. Community feedback will help confirm current waiting conditions and document where additional verification is valuable.";


                                if (
                                    detail.amenities?.wmata &&
                                    evidence.osm &&
                                    (
                                        (
                                            detail.amenities.wmata.shelter === "0" &&
                                            evidence.osm.osm_shelter === 1
                                        )
                                        ||
                                        (
                                            detail.amenities.wmata.bench === "0" &&
                                            evidence.osm.osm_bench === 1
                                        )
                                    )
                                ) {

                                    reviewReason =
                                        "Available records disagree about existing amenities at this stop. Public mapping suggests some waiting amenities may be present, while WMATA inventory does not show them. Your review will help confirm current conditions and identify whether improvements may be needed.";

                                }


                                else if (
                                    evidence.observations &&
                                    evidence.observations.length > 0
                                ) {

                                    reviewReason =
                                        "Community members have already provided feedback about this stop. Additional observations help improve confidence in the available information.";

                                }


                                else if (
                                    detail.wmata_evidence &&
                                    (
                                        detail.wmata_evidence.wmata_shelter === "1" ||
                                        detail.wmata_evidence.shelter === "1"
                                    )
                                ) {

                                    reviewReason =
                                        "Available records indicate this stop likely has a shelter. Your review will help confirm current conditions and identify whether additional waiting area improvements could better support riders.";

                                }


                                else if (
                                    evidence.osm &&
                                    evidence.osm.osm_shelter === 1 &&
                                    evidence.osm.osm_bench === 0
                                ) {

                                    reviewReason =
                                        "This stop appears to have a shelter, but seating information needs verification. Your review helps document current waiting conditions and available amenities.";

                                }


                                else if (
                                    detail.wmata_evidence &&
                                    detail.wmata_evidence.wmata_shelter === "0" &&
                                    evidence.osm &&
                                    evidence.osm.osm_shelter === 0 &&
                                    evidence.osm.osm_bench === 0
                                ) {

                                    reviewReason =
                                        "Available records do not show a shelter or bench. Your review helps confirm current stop conditions and improve the accuracy of public information.";

                                }



                                let popup = `
                                <b>${props.location.replace("+", " at ")}</b><br>

                                <br>

                                <b>Transit demand</b><br>

                                Routes serving this stop carry approximately

                                <b>
                                ${
                                    detail.impact_summary &&
                                    detail.impact_summary.estimated_weekday_boardings !== null &&
                                    detail.impact_summary.estimated_weekday_boardings !== undefined
                                    ? detail.impact_summary.estimated_weekday_boardings.toLocaleString()
                                    : "Unknown"
                                }
                                weekday boardings per day
                                </b>

                                on average.

                                <br><br>


                                Routes:
                                ${
                                    detail.impact_summary &&
                                    detail.impact_summary.routes &&
                                    detail.impact_summary.routes.length
                                    ? detail.impact_summary.routes.join(", ")
                                    : "Unknown"
                                }

                                <br><br>

                                <b>Rider exposure percentile:</b>
                                ${
                                    detail.impact_summary &&
                                    detail.impact_summary.rider_exposure_percentile !== null
                                    ? detail.impact_summary.rider_exposure_percentile + "th percentile"
                                    : "Unknown"
                                }


                                <br><br>

                                ${
                                    detail.community_review &&
                                    detail.community_review.has_reviewed
                                    ?
                                    `
                                    <b>✅ You have reviewed this stop</b><br>
                                    Community observations submitted:
                                    ${detail.community_review.review_count}
                                    `
                                    :
                                    `
                                    <b>Community review status:</b><br>
                                    No review submitted by you yet.
                                    `
                                }


                                <br><br>

                                <b>WMATA Stop IDs:</b>
				${
				    props.wmata_stop_ids && props.wmata_stop_ids.length
				        ? props.wmata_stop_ids.join(", ")
				        : "Unknown"
				}
				<br><br>

                                <b>Why this stop is being reviewed</b><br>

                                ${reviewReason}
                                <br><br>

                                <b>Current improvement projects</b><br>
                                `;


                                if (detail.projects && detail.projects.length > 0) {

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
                                    !detail.projects ||
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

                                        WMATA accessibility rating:
                                        ${
                                            detail.amenities.wmata.accessible === "Y"
                                            ? "Accessible"
                                            : detail.amenities.wmata.accessible === "N"
                                            ? "Not rated accessible"
                                            : "Unknown"
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


                                        ${
                                            detail.amenities?.wmata &&
                                            detail.amenities.wmata.shelter !==
                                            (evidence.osm.osm_shelter === 1 ? "1" : "0")
                                            ?
                                            `
                                            <br>
                                            <b>Data note:</b><br>
                                            WMATA inventory and public mapping sources differ on shelter status. A community review can help confirm current waiting conditions.<br>
                                            `
                                            :
                                            ""
                                        }
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
                                href="/review/${props.stop_id}?mode=opportunity"
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



        if(markers.length){

            map.fitBounds(
                L.featureGroup(markers).getBounds()
            );

        }



    }
);

}

if(routeFilter){

    routeFilter.addEventListener(
        "change",
        function(){

            loadStops();

        }
    );

}



if(document.getElementById("map")){

    map.createPane("markerPane");

    map.getPane("markerPane").style.zIndex = 400;

    map.getPane("popupPane").style.zIndex = 700;

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

        console.log("REQUESTING MAP:", url);
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








function loadRouteFilter(){

    fetch("/routes")

    .then(
        response => response.json()
    )

    .then(
        routes => {

            const selector =
                document.getElementById(
                    "routeFilter"
                );

            if(!selector){
                return;
            }


            routes.forEach(
                route => {

                    const option =
                        document.createElement(
                            "option"
                        );

                    option.value =
                        route.route_id;


                    option.textContent =
                        route.route_id +
                        " - " +
                        route.route_name;


                    selector.appendChild(
                        option
                    );

                }
            );

        }
    );

}



window.addEventListener(
    "load",
    loadRouteFilter
);


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

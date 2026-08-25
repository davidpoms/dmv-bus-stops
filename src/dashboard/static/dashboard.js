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
                    data.evidence?.reviews || []

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

                                const evidence = {

                                    osm:
                                        detail.evidence?.osm || {},

                                    observations:
                                        detail.evidence?.reviews || []

                                };

                                const amenityStatus = Object.fromEntries(
                                    (detail.amenity_status || []).map(
                                        item => [item.amenity_type, item.derived_status]
                                    )
                                );


                                let reviewReason =
                                    "This stop has been prioritized for community verification because available information suggests additional review would be valuable. Community feedback will help confirm current waiting conditions and document where additional verification is valuable.";


                                if (
                                    evidence.observations &&
                                    evidence.observations.length > 0
                                ) {

                                    reviewReason =
                                        "Community members have already provided feedback about this stop. Additional observations help improve confidence in the available information.";

                                }


                                else if (
                                    ["confirmed_yes", "likely_yes"].includes(
                                        amenityStatus.shelter
                                    ) &&
                                    ["likely_no", "conflicting", "unknown"].includes(
                                        amenityStatus.bench
                                    )
                                ) {

                                    reviewReason =
                                        "Canonical evidence suggests this stop has a shelter, but bench presence still needs verification. Your review helps document current waiting conditions and available amenities.";

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
                                        Steward this stop
                                    </button>
                                    `;

                                }


                                if (
                                    evidence.osm
                                ) {

                                    popup += `
                                    <br>
                                    <b>Existing stop information</b><br>
                                    `;


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

                                            Preliminary pass-through clearance:
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
                                href="/stop/${props.stop_id}"
                                class="stop-review-button">
                                View stop profile
                                </a>

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
                `/stops/${stopId}/steward`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                        "application/json"
                    },

                    body: JSON.stringify({})
                }
            )
            .then(
                response => response.json()
            )
            .then(
                data => {

                    alert(
                        "You are now a community steward for this stop!"
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

<td>${row.total_stops}</td>

<td title="Confirmed: ${row.shelter_confirmed_yes}; Likely: ${row.shelter_likely_yes}">${row.shelter_known_or_likely_present}</td>
<td title="Confirmed: ${row.shelter_confirmed_no}; Likely: ${row.shelter_likely_no}">${row.shelter_known_or_likely_absent}</td>
<td>${row.shelter_conflicting}</td>
<td>${row.shelter_unknown}</td>

<td title="Confirmed: ${row.bench_confirmed_yes}; Likely: ${row.bench_likely_yes}">${row.bench_known_or_likely_present}</td>
<td title="Confirmed: ${row.bench_confirmed_no}; Likely: ${row.bench_likely_no}">${row.bench_known_or_likely_absent}</td>
<td>${row.bench_conflicting}</td>
<td>${row.bench_unknown}</td>

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
            `${x.type} ${x.geography}`
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

async function loadCommunityProfileCard(){

    const card =
        document.getElementById(
            "communityProfileCard"
        );


    if(!card){
        return;
    }


    try {

        const response =
            await fetch(
                "/api/reviewer/status"
            );


        const data =
            await response.json();


        if(data.has_profile){

            card.style.display =
                "block";


            const name =
                document.getElementById(
                    "communityProfileName"
                );


            if(name){

                name.innerText =
                    data.display_name ||
                    "Community Volunteer";

            }

        }

    }

    catch(error){

        console.error(
            "Unable to load reviewer profile:",
            error
        );

    }

}



window.addEventListener(
    "load",
    loadCommunityProfileCard
);

let benchCandidateRows = [];

function humanizeBenchCandidateValue(value) {
    return String(value || "unknown")
        .replace(/_/g, " ")
        .replace(/\b\w/g, character => character.toUpperCase());
}

function renderBenchCandidates(rows) {
    const body = document.getElementById("benchCandidateBody");
    if (!body) return;
    body.innerHTML = rows.length ? rows.map(candidate => `
        <tr>
            <td>${candidate.opportunity_rank}</td>
            <td><a href="/stop/${candidate.physical_stop_id}">${candidate.primary_name || "Unnamed stop"}</a></td>
            <td>${[candidate.municipality, candidate.county, candidate.state].filter(Boolean).join(", ")}</td>
            <td>${candidate.priority_score.toFixed(1)}</td>
            <td>${candidate.rider_exposure_percentile.toFixed(1)}th percentile</td>
            <td>${candidate.documented_need_index.toFixed(0)} — ${humanizeBenchCandidateValue(candidate.strongest_need_signal)}</td>
            <td>${humanizeBenchCandidateValue(candidate.clearance_status)}</td>
            <td>${humanizeBenchCandidateValue(candidate.workflow_state)}</td>
        </tr>`).join("") : `<tr><td colspan="8">No matching candidates.</td></tr>`;
}

function filterBenchCandidates() {
    const query = (document.getElementById("benchCandidateSearch")?.value || "").toLowerCase();
    renderBenchCandidates(benchCandidateRows.filter(candidate =>
        JSON.stringify(candidate).toLowerCase().includes(query)
    ));
}

async function loadBenchCandidates() {
    if (!document.getElementById("benchCandidateBody")) return;
    try {
        const response = await fetch("/seating-opportunities");
        const data = await response.json();
        benchCandidateRows = data.opportunities || [];
        const summary = data.summary || {};
        document.getElementById("benchCandidateMetrics").innerHTML = `
            <strong>${summary.total_active_stops || 0}</strong> active stops &middot;
            <strong>${summary.bench_absent || 0}</strong> likely/confirmed bench absent &middot;
            <strong>${summary.bench_presence_unknown || 0}</strong> presence unknown &middot;
            <strong>${summary.observed_seating_limitation || 0}</strong> observed limitation`;
        renderBenchCandidates(benchCandidateRows);
    } catch (error) {
        document.getElementById("benchCandidateBody").innerHTML =
            `<tr><td colspan="8">Seating opportunities are unavailable.</td></tr>`;
    }
}

window.addEventListener("load", loadBenchCandidates);

async function loadOpportunityCampaignCounts() {
    const targets = {
        campaignPresenceCount: "verify_presence",
        campaignAdequacyCount: "assess_adequacy",
        campaignClearanceCount: "collect_clearance_observation",
        campaignPlanningCount: "planning_review"
    };
    if (!document.getElementById("campaignAllCount")) return;
    try {
        const response = await fetch("/seating-opportunities");
        const payload = await response.json();
        const workflow = (payload.summary && payload.summary.workflow) || {};
        const assignable = Object.entries(workflow)
            .filter(([state]) => state !== "no_current_action")
            .reduce((sum, [, count]) => sum + count, 0);
        document.getElementById("campaignAllCount").textContent =
            `(${assignable.toLocaleString()})`;
        Object.entries(targets).forEach(([id, state]) => {
            document.getElementById(id).textContent =
                `(${(workflow[state] || 0).toLocaleString()})`;
        });
    } catch (error) {
        console.warn("Could not load seating opportunity campaign counts", error);
    }
}

window.addEventListener("load", loadOpportunityCampaignCounts);


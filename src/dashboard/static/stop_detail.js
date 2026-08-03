
async function loadStopProfile(){

    const details =
        document.getElementById("details");


    try {

        const stopResponse =
            await fetch(`/stops/${stopId}`);

        const stop =
            await stopResponse.json();


        const reviewResponse =
            await fetch(`/review/${stopId}/info`);

        const review =
            await reviewResponse.json();



        document.getElementById("name").innerHTML =
            stop.location || review.name || "Bus Stop";



        details.innerHTML = `

        <div class="card">

        <strong>Location</strong><br>

        ${stop.location || review.name}

        <br><br>

        Stop ID:
        ${stop.stop_id}

        <br><br>

        Routes:
        ${(stop.routes || []).join(", ")}

        </div>



        <div class="card">

        <strong>Rider exposure</strong>

        <br><br>

        Estimated weekday boardings:

        <strong>
        ${
            review.impact_summary
            ?.estimated_weekday_boardings
            ?.toLocaleString()
            || "Unknown"
        }
        </strong>


        <br><br>

        Opportunity score:

        <strong>
        ${stop.score || "Unknown"}
        </strong>


        </div>



        <div class="card">

        <strong>
        Current stop information
        </strong>

        <br><br>

        WMATA status:

        ${
            review.wmata?.status || "Unknown"
        }

        <br>

        Shelter:

        ${
            review.wmata?.shelter == 1
            ? "Yes"
            : "No"
        }

        <br>

        Bench:

        ${
            review.wmata?.bench == 1
            ? "Yes"
            : "No"
        }


        </div>



        <div class="card">

        <strong>
        Community verification
        </strong>

        <br><br>

        Reviews completed:

        ${
            review.community_reviews?.review_count || 0
        }


        <br><br>

        <a
        class="stop-review-button"
        href="/review/${stopId}?mode=opportunity">

        Review this stop

        </a>


        <br><br>


        <a
        class="stop-review-button"
        href="${stop.streetview_url}"
        target="_blank">

        Open Street View

        </a>


        </div>

        `;



    }
    catch(error){

        console.error(
            "Failed loading stop profile",
            error
        );

        details.innerHTML =
            "Unable to load stop information.";

    }

}


loadStopProfile();


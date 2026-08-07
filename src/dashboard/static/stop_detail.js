async function loadStopProfile(){

    const details = document.getElementById("details");

    try {

        const stopResponse = await fetch(`/stops/${stopId}`);
        const stop = await stopResponse.json();

        const reviewResponse = await fetch(`/review/${stopId}/info`);
        const review = await reviewResponse.json();


        console.log("STOP DATA", stop);
        console.log("REVIEW DATA", review);


        document.getElementById("name").innerHTML =
            stop.location ||
            stop.stop_name ||
            review.name ||
            "Bus Stop";


        const routeIds =
            stop.impact_summary?.routes ||
            review.impact_summary?.routes ||
            review.ridership_exposure?.routes ||
            [];


        const routeNames =
            stop.routes ||
            review.routes ||
            [];


        let routeText = "No route data";


        if (
            Array.isArray(routeIds) &&
            Array.isArray(routeNames)
        ) {

            const combined = [];


            const count =
                Math.max(
                    routeIds.length,
                    routeNames.length
                );


            for (
                let i = 0;
                i < count;
                i++
            ) {

                const id =
                    routeIds[i] || "";

                const name =
                    routeNames[i] || "";


                if (id && name) {

                    combined.push(
                        `${id} — ${name}`
                    );

                }

                else if (id) {

                    combined.push(id);

                }

                else if (name) {

                    combined.push(name);

                }

            }


            routeText =
                combined.join("<br>");

        }

        else if (Array.isArray(routeNames)) {

            routeText =
                routeNames.join("<br>");

        }


        const boardings =
            review.impact_summary?.estimated_weekday_boardings ||
            review.daily_route_exposure ||
            stop.daily_route_exposure ||
            null;


        const score =
            stop.score ??
            stop.opportunity_score ??
            stop.impact_score ??
            review.opportunity_score ??
            "Unknown";


        const shelter =
            review.wmata?.shelter ??
            stop.wmata?.shelter;


        const bench =
            review.wmata?.bench ??
            stop.wmata?.bench;


        const streetview =
            stop.streetview_url ||
            review.streetview_url ||
            "#";


        details.innerHTML = `


        <div class="card">

            <strong>Location</strong><br>

            ${stop.location || review.name || "Unknown"}

            <br><br>

            Internal ID:
            ${stop.stop_id || stopId}

            <br><br>

            Routes:
            ${routeText}

        </div>



        <div class="card">

            <strong>
            Stop information
            </strong>

            <br><br>


            Routes served:

            <strong>
            ${routeText}
            </strong>


            <br><br>


            Estimated weekday boardings:

            <strong>
            ${
                boardings
                ? Number(boardings).toLocaleString()
                : "Unknown"
            }
            </strong>


            <br><br>


            Rider exposure percentile:

            <strong>
            ${
                stop.impact_summary?.rider_exposure_percentile
                ?
                stop.impact_summary.rider_exposure_percentile + "th percentile"
                :
                "Unknown"
            }
            </strong>


            <br><br>


            Opportunity score:

            <strong>
            ${score}
            </strong>


            <br><br>


            <strong>
            Amenity status
            </strong>


            <br><br>


            Shelter:

            ${
                stop.ddot_interpretation &&
                stop.ddot_interpretation.some(
                    item =>
                    item.evidence_class ===
                    "current_asset"
                )
                ?
                "✓ DDOT shelter asset identified"
                :
                "No confirmed evidence"
            }


            <br><br>


            Bench:

            No confirmed evidence


            <br><br>


            <strong>
            Evidence sources
            </strong>


            <br><br>


            ${
                stop.ddot_interpretation &&
                stop.ddot_interpretation.length
                ?

                stop.ddot_interpretation.map(
                    item => `

                    <div>

                        <strong>
                        ${item.public_status || item.source}
                        </strong>

                        <br>

                        ${item.finding}

                        <br>

                        Confidence:

                        <strong>
                        ${item.confidence}
                        </strong>


                        ${
                            item.source_record
                            ?
                            `<br>
                            Source record:
                            ${item.source_record}`
                            :
                            ""
                        }


                        ${
                            item.routes &&
                            item.routes.length
                            ?
                            `<br>
                            Routes:
                            ${item.routes.join(", ")}`
                            :
                            ""
                        }

                    </div>

                    <br>

                    `
                ).join("")

                :

                "No external evidence available."

            }


        </div>



        <div class="card">

            <strong>
            Community verification
            </strong>


            <br><br>

            Reviews completed:

            ${
                review.community_reviews?.review_count ||
                stop.community_review?.total_stop_reviews ||
                0
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
            href="${streetview}"
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
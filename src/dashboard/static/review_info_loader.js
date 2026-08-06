document.addEventListener(
    "DOMContentLoaded",
    async () => {

        const stopId =
            window.location.pathname.split("/").pop();


        function displayAmenity(value) {

            if (
                value === true ||
                value === 1 ||
                value === "yes" ||
                value === "Yes"
            ) {
                return "Yes";
            }

            if (
                value === false ||
                value === 0 ||
                value === "no" ||
                value === "No"
            ) {
                return "No";
            }

            return "Not reported";
        }


        const container =
            document.getElementById("stopInfo");


        if (!container) {
            return;
        }


        try {

            const response =
                await fetch(
                    `/review/${stopId}/info`
                );


            const info =
                await response.json();

            console.log(
                "Loaded review info:",
                info
            );


            container.innerHTML = `
                <div class="panel">

                    <strong>
                    ${info.name || "Bus Stop"}
                    </strong>

                    <br>

                    Stop ID:
                    ${info.stop_id}

                    <br><br>

                    Coordinates:
                    ${info.lat.toFixed(5)},
                    ${info.lon.toFixed(5)}

                    <br><br>

                    Jurisdiction:
                    ${info.state || ""}
                    ${info.county ? " | " + info.county : ""}
                    ${info.municipality ? " | " + info.municipality : ""}

                    <br><br>

                    Serving direction:

                    <strong>
                    ${
                        (() => {
                            const heading = Number(
                                info.serving_direction
                            );

                            if (isNaN(heading)) {
                                return "Unknown";
                            }

                            if (heading < 22.5 || heading >= 337.5)
                                return "North";

                            if (heading < 67.5)
                                return "Northeast";

                            if (heading < 112.5)
                                return "East";

                            if (heading < 157.5)
                                return "Southeast";

                            if (heading < 202.5)
                                return "South";

                            if (heading < 247.5)
                                return "Southwest";

                            if (heading < 292.5)
                                return "West";

                            return "Northwest";

                        })()
                    }
                    </strong>

                    <br><br>
                    ${
                        info.impact_summary &&
                        info.impact_summary.rider_exposure_percentile
                        ?
                        `
                        <div class="evidence-card">

                            <strong>
                            Why this stop was selected
                            </strong>

                            <br><br>

                            Verification priorities consider rider exposure
                            and the need for better information about current
                            stop conditions.

                            <br><br>

                            <strong>
                            Rider exposure
                            </strong>

                            <br><br>

                            The routes serving this stop carry more riders
                            than approximately

                            <strong>
                            ${
                                Math.min(
                                    info.impact_summary.rider_exposure_percentile,
                                    99
                                )
                            }%
                            </strong>

                            of stops in the region.

                            <br><br>

                            Estimated route exposure:

                            <strong>
                            ${
                                info.impact_summary.estimated_weekday_boardings
                                ? info.impact_summary.estimated_weekday_boardings.toLocaleString()
                                : "Unknown"
                            }
                            weekday boardings across
                            ${
                                info.impact_summary.routes_served || 0
                            }
                            serving routes
                            </strong>

                            <br><br>

                            Routes:

                            ${
                                info.impact_summary.routes &&
                                info.impact_summary.routes.length
                                ? info.impact_summary.routes.join(", ")
                                : "Unknown"
                            }

                            <br><br>

                            <small>
                            Rider exposure is estimated using route-level
                            ridership data associated with this stop.
                            Stop-level boarding counts are not available.
                            </small>

                        </div>

                        <br>
                        `
                        :
                        ""
                    }


                    ${
                        info.impact_summary
                        ?
                        `
                        <div class="evidence-card">

                            <strong>
                            Community verification need
                            </strong>

                            <br><br>

                            Available records do not fully confirm current
                            waiting conditions.

                            <br><br>

                            Your review helps improve the accuracy of stop
                            information and identify where improvements may
                            be needed.

                        </div>

                        <br>
                        `
                        :
                        ""
                    }



                    ${
                        info.wmata
                        ?
                        `
                        <div class="evidence-card">

                            <strong>
                            Current Stop Amenities (WMATA)
                            </strong>

                            <br><br>

                            WMATA Data Availability:
                            <span class="${
                                info.wmata.availability === "confirmed"
                                ? "wmata-confirmed"
                                : "wmata-unavailable"
                            }">
                            ${
                                info.wmata.availability === "confirmed"
                                ? "Confirmed WMATA match"
                                : "No WMATA match available"
                            }
                            </span>

                            <br><br>

                            WMATA Stop ID:
                            ${info.wmata.stop_id || "Unknown"}

                            <br>

                            Status:
                            ${
                                info.wmata.status === "PRS"
                                ? "Published stop"
                                : (info.wmata.status || "Unknown")
                            }

                            <br>

                            Shelter:
                            ${
                                info.wmata.shelter === "1"
                                ? "Yes"
                                : info.wmata.shelter === "0"
                                ? "No"
                                : "Unknown"
                            }

                            <br>

                            Bench:
                            ${
                                info.wmata.bench === "1"
                                ? "Yes"
                                : info.wmata.bench === "0"
                                ? "No"
                                : "Unknown"
                            }

                            <br>

                            Accessible:
                            ${
                                info.wmata.accessible === "Y"
                                ? "Yes"
                                : "No"
                            }

                            <br>

                            Match quality:
                            ${
                                info.wmata.match_confidence === "high"
                                ? "High confidence match (within ~10 meters)"
                                : info.wmata.match_confidence === "medium"
                                ? "Medium confidence match (within ~50 meters)"
                                : info.wmata.match_confidence === "low"
                                ? "Low confidence match (verify location)"
                                : "Unknown"
                            }

                            <br>

                            Match distance:
                            ${
                                info.wmata.match_distance_m !== null
                                ? (
                                    info.wmata.match_distance_m < 10
                                    ? info.wmata.match_distance_m.toFixed(1)
                                    : Math.round(info.wmata.match_distance_m)
                                ) + " meters"
                                : "Unknown"
                            }

                        </div>

                        <br>
                        `
                        :
                        ""
                    }


                    ${
                        info.community_reviews &&
                        info.community_reviews.review_count > 0
                        ?
                        `
                        <div class="evidence-card">

                            <strong>
                            Community observations
                            </strong>

                            <br><br>

                            ${info.community_reviews.review_count}
                            observation(s)

                            <br><br>

                            ${
                                info.community_reviews.reviews.map(
                                    review => `
                                    <strong>
                                    ${review.date}
                                    </strong>

                                    <br><br>

                                    Shelter:
                                    ${displayAmenity(review.shelter)}

                                    <br>

                                    Bench:
                                    ${displayAmenity(review.bench)}

                                    <br><br>

                                    Notes:
                                    ${
                                        review.notes &&
                                        review.notes.trim()
                                        ? review.notes
                                        : "No notes provided."
                                    }

                                    <br><br>
                                    `
                                ).join("")
                            }

                        </div>

                        <br>
                        `
                        :
                        ""
                    }


                    ${
                        info.streetview_url
                        ?
                        `
                        <br><br>

                        <a
                            href="${info.streetview_url}"
                            target="_blank"
                            class="stop-review-button">

                            Open Google Street View

                        </a>
                        `
                        :
                        ""
                    }

                </div>
            `;


        } catch(error){

            console.error(
                "Failed loading stop info",
                error
            );

            container.innerHTML =
                "Unable to load stop information.";

        }

    }
);

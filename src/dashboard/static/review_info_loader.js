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

                    Internal ID:
                    ${info.stop_id}

                    <br><br>

                    External Stop ID:
                    ${info.external_stop_id || "Not recorded"}

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
                        info.amenity_evidence &&
                        info.amenity_evidence.length > 0
                        ?
                        `
                        <div class="evidence-card">

                            <strong>
                            Local jurisdiction evidence
                            </strong>

                            <br><br>

                            Supporting records for shelter and bench
                            presence. These records have not been
                            independently verified by a community
                            observation.

                            <br><br>

                            ${
                                (() => {

                                    const grouped = {};

                                    info.amenity_evidence
                                    .filter(
                                        evidence =>
                                            evidence.amenity_type === "shelter" ||
                                            evidence.amenity_type === "bench"
                                    )
                                    .forEach(
                                        evidence => {

                                            const key =
                                                (
                                                    evidence.jurisdiction ||
                                                    evidence.source ||
                                                    "Local jurisdiction"
                                                )
                                                + "|"
                                                + (
                                                    evidence.source_record ||
                                                    ""
                                                );

                                            if (!grouped[key]) {

                                                grouped[key] = {
                                                    jurisdiction:
                                                        evidence.jurisdiction ||
                                                        evidence.source ||
                                                        "Local jurisdiction",

                                                    source_record:
                                                        evidence.source_record ||
                                                        null,

                                                    confidence:
                                                        evidence.confidence ||
                                                        "Unknown",

                                                    match_distance_m:
                                                        evidence.match_distance_m,

                                                    shelter: null,

                                                    bench: null
                                                };
                                            }

                                            if (
                                                evidence.amenity_type ===
                                                "shelter"
                                            ) {
                                                grouped[key].shelter =
                                                    evidence.present
                                                    ? "Yes"
                                                    : "No";
                                            }

                                            if (
                                                evidence.amenity_type ===
                                                "bench"
                                            ) {
                                                grouped[key].bench =
                                                    evidence.present
                                                    ? "Yes"
                                                    : "No";
                                            }
                                        }
                                    );

                                    return Object.values(grouped)
                                    .map(
                                        evidence => `

                                        <strong>
                                        ${
                                            evidence.jurisdiction ===
                                            "MONTGOMERY_COUNTY"
                                            ? "Montgomery County"
                                            : evidence.jurisdiction ||
                                              "Local jurisdiction"
                                        }
                                        </strong>

                                        <br><br>

                                        Shelter:
                                        <strong>
                                        ${
                                            evidence.shelter ||
                                            "Not recorded"
                                        }
                                        </strong>

                                        <br>

                                        Bench:
                                        <strong>
                                        ${
                                            evidence.bench ||
                                            "Not recorded"
                                        }
                                        </strong>

                                        <br>

                                        Confidence:
                                        ${
                                            evidence.confidence
                                        }

                                        <br>

                                        Match distance:
                                        ${
                                            evidence.match_distance_m !== null
                                            ? evidence.match_distance_m.toFixed(1) + " m"
                                            : "Unknown"
                                        }

                                        <br>

                                        Source record:
                                        ${
                                            evidence.source_record ||
                                            "Not recorded"
                                        }

                                        <br><br>
                                        `
                                    )
                                    .join("");

                                })()
                            }

                        </div>

                        <br>
                        `
                        :
                        ""
                    }


                    <div class="evidence-card">

                        <strong>
                        Community observations
                        </strong>

                        <br><br>

                        ${
                            info.community_reviews &&
                            info.community_reviews.review_count > 0
                            ?
                            `
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
                            `
                            :
                            `
                            No observations yet.

                            <br><br>

                            Be the first to review this stop.
                            `
                        }

                    </div>

                    <br>

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

                    ${
                        info.wmata_rider_tools_url
                        ?
                        `
                        <br><br>

                        <a
                            href="${info.wmata_rider_tools_url}"
                            target="_blank"
                            rel="noopener noreferrer"
                            class="stop-review-button">

                            Open WMATA Rider Tools

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

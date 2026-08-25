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

            const assignmentId = new URLSearchParams(window.location.search)
                .get("assignment_id");
            const infoUrl = `/review/${stopId}/info` +
                (assignmentId ? `?assignment_id=${encodeURIComponent(assignmentId)}` : "");
            const response = await fetch(infoUrl);


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

                    ${
                        info.review_context && info.review_context.scenario === "opportunity" &&
                        info.seating_improvement_opportunity
                        ? (() => {
                            const opportunity = info.seating_improvement_opportunity;
                            const labels = {
                                presence_verification: "Verify Seating",
                                seating_adequacy: "Assess Seating Comfort",
                                bench_clearance: "Check Bench Clearance",
                                planning_review: "Planning Review",
                                constrained_review: "Constrained/Special Review"
                            };
                            const rationale = Array.isArray(opportunity.rationale)
                                ? opportunity.rationale.join(" ") : "";
                            return `
                            <div class="evidence-card opportunity-review-context">
                                <strong>${labels[info.review_context.campaign] || "All Seating Opportunities"}</strong><br><br>
                                Bench: ${opportunity.bench_status}<br>
                                Shelter: ${opportunity.shelter_status}<br>
                                Seating adequacy: ${opportunity.adequacy_status}<br>
                                Preliminary clearance: ${opportunity.clearance_status}<br>
                                Documented need index: ${opportunity.documented_need_index}<br>
                                Strongest documented need: ${opportunity.strongest_need_signal}<br>
                                Rider exposure percentile: ${opportunity.rider_exposure_percentile}<br>
                                Provisional seating-improvement priority: ${opportunity.priority_score}<br>
                                Next evidence action: ${opportunity.workflow_state}<br><br>
                                ${rationale}<br><br>
                                <small>The score ranks opportunities; it does not gate eligibility.
                                Rider exposure is route-based, not observed stop-level boardings.
                                Preliminary clearance is not engineering feasibility, ADA compliance,
                                ownership or permitting approval, utility clearance, or construction readiness.</small>
                            </div><br>`;
                        })()
                        : ""
                    }

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

                            ${
                                info.amenity_review_priority &&
                                info.amenity_review_priority.length
                                ? `<strong>${info.amenity_review_priority[0].amenity_type}:</strong>
                                   ${info.amenity_review_priority[0].reason}<br><br>`
                                : ""
                            }

                            Verification priorities consider rider exposure
                            and the need for better information about current
                            stop conditions.

                            <br><br>

                            <strong>
                            Rider exposure percentile
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

                            This is a route-based exposure estimate, not
                            observed stop-level ridership.

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

                            Supporting amenity records from local
                            jurisdictions. Community observations are
                            shown separately.

                            <br><br>

                            ${
                                LocalEvidenceUI.render(info.amenity_evidence)
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

                                    <br>

                                    Review method: ${review.review_mode || "Legacy/unspecified"}

                                    <br>

                                    Assignment: ${review.assignment_id || "Legacy observation"}

                                    ${review.streetview_imagery_month ? `<br>Street View imagery month: ${review.streetview_imagery_month}` : ""}

                                    ${review.preliminary_clearance ? `<br>Preliminary clearance observation: ${review.preliminary_clearance}` : ""}

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

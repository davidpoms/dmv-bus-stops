async function loadStopProfile() {
    const details = document.getElementById("details");

    try {
        const stopResponse = await fetch(`/stops/${stopId}`);
        const stop = await stopResponse.json();

        const reviewResponse = await fetch(`/review/${stopId}/info`);
        const review = await reviewResponse.json();

        const communityResponse =
            await fetch(`/stops/${stopId}/community-reviews`);

        const communityData =
            await communityResponse.json();

        console.log("STOP DATA", stop);
        console.log("REVIEW DATA", review);
        console.log("COMMUNITY REVIEWS", communityData);

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

            for (let i = 0; i < count; i++) {
                const id = routeIds[i] || "";
                const name = routeNames[i] || "";

                if (id && name) {
                    combined.push(`${id} &mdash; ${name}`);
                } else if (id) {
                    combined.push(id);
                } else if (name) {
                    combined.push(name);
                }
            }

            routeText = combined.join("<br>");
        } else if (Array.isArray(routeNames)) {
            routeText = routeNames.join("<br>");
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

        const streetview =
            stop.streetview_url ||
            review.streetview_url ||
            "#";

        const riderToolsUrl =
            stop.wmata_rider_tools_url ||
            review.wmata_rider_tools_url ||
            null;

        const communityReviews =
            Array.isArray(communityData)
                ? communityData
                : communityData.reviews || [];


        const recommendations =
            Array.isArray(stop.recommendations)
                ? stop.recommendations
                : [];

        const opportunityRecommendations =
            Array.isArray(stop.opportunity?.recommendations)
                ? stop.opportunity.recommendations
                : [];


        function recommendationLabel(type) {

            const labels = {

                bench_presence_review:
                    "Bench presence needs verification",

                shelter_presence_review:
                    "Shelter presence needs verification",

                bench_installation_candidate:
                    "Bench installation candidate",

                shelter_installation_candidate:
                    "Shelter installation candidate",

                seating_review:
                    "Seating information needs verification",

                seating_review_needed:
                    "Seating information needs verification",

                comfort_upgrade_candidate:
                    "Rider comfort improvement opportunity",

                bench_feasibility_review:
                    "Bench installation feasibility review",

                accessibility_review:
                    "Accessibility information needs verification",

                general_amenity_review:
                    "Amenity information needs verification"

            };

            return labels[type] || "Improvement review";
        }


        function recommendationPriority(priority) {

            if (!priority) {
                return "Not specified";
            }

            return String(priority)
                .replace(/_/g, " ")
                .replace(/\b\w/g, char => char.toUpperCase());
        }


        function recommendationConfidence(confidence) {

            if (!confidence) {
                return "Not specified";
            }

            return String(confidence)
                .replace(/_/g, " ")
                .replace(/\b\w/g, char => char.toUpperCase());
        }


        function opportunityLabel(type) {

            const labels = {

                priority_review:
                    "Priority review",

                ridership_based_improvement_review:
                    "Ridership-based improvement review"

            };

            return labels[type] || "Additional review";
        }


        const assessmentHtml =
            opportunityRecommendations.length
                ? `

                    <div class="card assessment-card">

                        <strong>
                            Current assessment
                        </strong>

                        <p>
                            This stop has been identified for additional
                            verification or follow-up based on available
                            transit and rider-exposure evidence.
                        </p>

                        <div class="assessment-list">

                            ${opportunityRecommendations.map(
                                recommendation => `

                                    <div class="assessment-item">

                                        <strong>
                                            ${opportunityLabel(
                                                recommendation
                                            )}
                                        </strong>

                                    </div>

                                `
                            ).join("")}

                        </div>

                        <p class="assessment-note">
                            This assessment does not by itself indicate
                            that a physical improvement should be installed.
                            Specific improvement recommendations require
                            additional evidence.
                        </p>

                    </div>

                `
                : "";


        const recommendationHtml =
            recommendations.length
                ? recommendations.map(rec => `

                    <div class="recommendation-item">

                        <div class="recommendation-header">

                            <strong>
                                ${recommendationLabel(rec.type)}
                            </strong>

                        </div>

                        <p class="recommendation-description">
                            The available evidence supports consideration
                            of this potential improvement or follow-up action.
                            Community evidence and local conditions should
                            still be considered before implementation.
                        </p>

                        <div class="recommendation-meta">

                            <span>
                                Priority:
                                <strong>
                                    ${recommendationPriority(rec.priority)}
                                </strong>
                            </span>

                            <span>
                                Confidence:
                                <strong>
                                    ${recommendationConfidence(rec.confidence)}
                                </strong>
                            </span>

                        </div>

                        ${
                            Array.isArray(rec.reasons) &&
                            rec.reasons.length
                                ? `

                                    <div class="recommendation-reasons-title">
                                        Why this stop was flagged
                                    </div>

                                    <ul class="recommendation-reasons">

                                        ${rec.reasons.map(reason => `
                                            <li>
                                                ${reason}
                                            </li>
                                        `).join("")}

                                    </ul>

                                `
                                : ""
                        }

                        <div class="recommendation-action">

                            <a
                                href="/review/${stopId}?mode=opportunity"
                                class="recommendation-review-button"
                            >
                                Review this stop
                            </a>

                        </div>

                    </div>

                `).join("")

                : `

                    <div class="recommendation-empty">

                        No specific physical improvement recommendation
                        is currently generated for this stop.

                        <div class="recommendation-action-note">
                            The current assessment may still indicate that
                            additional verification is useful.
                        </div>

                    </div>

                `;


        function amenityValue(value) {
            if (
                value === 1 ||
                value === true ||
                value === "1" ||
                value === "yes" ||
                value === "Yes" ||
                value === "YES"
            ) {
                return "Yes";
            }

            if (
                value === 0 ||
                value === false ||
                value === "0" ||
                value === "no" ||
                value === "No" ||
                value === "NO"
            ) {
                return "No";
            }

            return "Not recorded";
        }

        const localEvidence =
    Array.isArray(review.amenity_evidence)
    ? review.amenity_evidence.filter(
        item =>
            item.amenity_type === "shelter" ||
            item.amenity_type === "bench"
      )
    : [];


const localEvidenceGroups = {};

localEvidence.forEach(item => {

    const key =
        (item.jurisdiction || item.source || "Local jurisdiction")
        + "|"
        + (item.source_record || "");

    if (!localEvidenceGroups[key]) {

        localEvidenceGroups[key] = {

            jurisdiction:
                item.jurisdiction ||
                item.source ||
                "Local jurisdiction",

            source_record:
                item.source_record ||
                null,

            confidence:
                item.confidence ||
                "Unknown",

            match_distance_m:
                item.match_distance_m,

            shelter: null,

            bench: null
        };
    }

    if (item.amenity_type === "shelter") {

        localEvidenceGroups[key].shelter =
            amenityValue(item.value ?? item.present);
    }

    if (item.amenity_type === "bench") {

        localEvidenceGroups[key].bench =
            amenityValue(item.value ?? item.present);
    }
});


const localEvidenceHtml =
    Object.values(localEvidenceGroups).length
    ? Object.values(localEvidenceGroups).map(item => `

        <div class="evidence-item">

            <strong>
                ${
                    item.jurisdiction === "MONTGOMERY_COUNTY"
                    ? "Montgomery County"
                    : item.jurisdiction ||
                      "Local jurisdiction"
                }
            </strong>

            <br><br>

            Shelter:
            <strong>
                ${item.shelter || "Not recorded"}
            </strong>

            <br>

            Bench:
            <strong>
                ${item.bench || "Not recorded"}
            </strong>

            <br>

            ${
                item.source === "DDOT"
                ? `
                    Source:
                    <strong>
                        DDOT shelter asset record
                    </strong>

                    <br>
                `
                : ""
            }

            Source record:
            ${item.source_record || "Not recorded"}

        </div>

    `).join("")
    : `
        <div class="community-observations-empty">
            No current local jurisdiction amenity record available.
        </div>
    `;


const latestCommunity =
            communityReviews.length
                ? communityReviews[0]
                : null;

        const communityShelter =
            latestCommunity
                ? amenityValue(latestCommunity.shelter)
                : "Not currently verified";

        const communityBench =
            latestCommunity
                ? amenityValue(latestCommunity.bench)
                : "Not currently verified";
        function formatReviewDate(value) {
            if (!value) {
                return "Date not recorded";
            }

            const date = new Date(value);

            if (Number.isNaN(date.getTime())) {
                return value;
            }

            return date.toLocaleDateString(
                "en-US",
                {
                    year: "numeric",
                    month: "short",
                    day: "numeric"
                }
            );
        }

        const communityHistoryHtml =
            communityReviews.length
                ? communityReviews.map(reviewItem => `
                    <div class="community-observation">

                        <div class="community-observation-header">
                            <strong>
                                Community observation
                            </strong>

                            <span class="community-observation-date">
                                ${formatReviewDate(reviewItem.date || reviewItem.observed_at)}
                            </span>
                        </div>

                        <div class="community-observation-grid">

                            <div>
                                <span class="community-observation-label">
                                    Shelter
                                </span>

                                <strong>
                                    ${amenityValue(reviewItem.shelter)}
                                </strong>
                            </div>

                            <div>
                                <span class="community-observation-label">
                                    Bench
                                </span>

                                <strong>
                                    ${amenityValue(reviewItem.bench)}
                                </strong>
                            </div>

                        </div>

                        ${
                            reviewItem.notes
                                ? `
                                    <div class="community-observation-notes">
                                        <span class="community-observation-label">
                                            Notes
                                        </span>

                                        <div>
                                            ${reviewItem.notes}
                                        </div>
                                    </div>
                                `
                                : ""
                        }

                    </div>
                `).join("")
                : `
                    <div class="community-observations-empty">
                        No community observations yet.
                        Be the first to review this stop.
                    </div>
                `;

        const ddotEvidenceHtml =
            stop.ddot_interpretation &&
            stop.ddot_interpretation.length
                ? stop.ddot_interpretation.map(item => {

                    const ddotSourceLabel =
                        item.source_type === "api"
                            ? "DDOT API shelter asset record"
                            : item.source_type === "procurement"
                                ? "DDOT shelter procurement inventory"
                                : item.source || "DDOT evidence record";

                    return `
                    <div class="ddot-evidence-item">

                        <strong>
                            ${ddotSourceLabel}
                        </strong>

                        <br><br>

                        ${item.finding || "Finding not recorded."}

                        <br><br>

                        Confidence:

                        <strong>
                            ${item.confidence || "Unknown"}
                        </strong>

                        ${
                            item.source_record
                                ? `
                                    <br><br>
                                    Source record:
                                    ${item.source_record}
                                `
                                : ""
                        }

                        ${
                            item.routes &&
                            item.routes.length
                                ? `
                                    <br><br>
                                    Routes:
                                    ${item.routes.join(", ")}
                                `
                                : ""
                        }

                    </div>
                    `;
                }).join("")
                : "No DDOT evidence available.";

        details.innerHTML = `

            <div class="card">

                <strong>Location</strong><br>

                ${stop.location || review.name || "Unknown"}

                <br><br>

                Internal ID:
                ${stop.stop_id || stopId}

                <br><br>
                External Stop ID:
                ${stop.external_stop_id || "Not recorded"}

                <br><br>


                Routes:
                ${routeText}

            </div>


            <div class="card rider-exposure-card">

                <strong>
                    Rider exposure
                </strong>

                <p>
                    This stop's serving routes represent a high level
                    of rider exposure compared with other stops in the region.
                </p>

                ${
                    stop.impact_summary &&
                    stop.impact_summary.rider_exposure_percentile
                        ? `
                        <div class="evidence-card">

                            <strong>
                                Rider exposure percentile
                            </strong>

                            <br><br>

                            The routes serving this stop carry more riders
                            than approximately

                            <strong>
                                ${
                                    Math.min(
                                        stop.impact_summary.rider_exposure_percentile,
                                        99
                                    )
                                }%
                            </strong>

                            of stops in the region.

                        </div>
                        `
                        : ""
                }

                <br>

                <div class="amenity-comparison">

                    <div class="amenity-comparison-row">

                        <strong>
                            Estimated route exposure
                        </strong>

                        <span>
                            <strong>
                                ${
                                    stop.impact_summary?.estimated_weekday_boardings
                                        ? stop.impact_summary.estimated_weekday_boardings.toLocaleString()
                                        : "Unknown"
                                }
                            </strong>
                            weekday boardings across
                            ${
                                stop.impact_summary?.routes_served || 0
                            }
                            serving routes
                        </span>

                    </div>

                    <div class="amenity-comparison-row">

                        <strong>
                            Routes served
                        </strong>

                        <span>
                            ${
                                stop.impact_summary?.routes &&
                                stop.impact_summary.routes.length
                                    ? stop.impact_summary.routes.join(", ")
                                    : "Unknown"
                            }
                        </span>

                    </div>

                </div>

                <p class="impact-note">
                    Rider exposure is estimated using route-level
                    ridership data associated with this stop.
                    These figures do not represent unique riders
                    or stop-level boardings.
                </p>

            </div>


            ${assessmentHtml}

            <div class="card recommendation-card">

                <strong>
                    Potential improvement recommendations
                </strong>

                <p>
                    These recommendations are generated only when the
                    available evidence supports consideration of a more
                    specific improvement or follow-up action.
                </p>

                <div class="recommendation-list">

                    ${recommendationHtml}

                </div>

            </div>


            <div class="card">
                <strong>
                    Community-verified amenity status
                </strong>

                <p>
                    Status reflects the latest community observation
                    when one is available. Local jurisdiction records
                    are shown separately as supporting evidence.
                </p>

                <div class="amenity-comparison">

                    <div class="amenity-comparison-row">

                        <strong>
                            Shelter
                        </strong>

                        <span>
                            Community observation:
                            <strong>${communityShelter}</strong>
                        </span>

                    </div>

                    <div class="amenity-comparison-row">

                        <strong>
                            Bench
                        </strong>

                        <span>
                            Community observation:
                            <strong>${communityBench}</strong>
                        </span>

                    </div>

                </div>

                <br>

                <strong>
                    Local jurisdiction evidence
                </strong>

                <p>
                    Supporting records for shelter and bench presence.
                    These records have not been independently verified
                    by a community observation.
                </p>

                <br><br>

                ${localEvidenceHtml}

            </div>


            <div class="card community-observations-card">

                <div class="community-observations-title">

                    <div>
                        <strong>
                            Community observations
                        </strong>

                        <div class="community-observations-subtitle">
                            ${
                                communityReviews.length
                                    ? `${communityReviews.length} observation${
                                        communityReviews.length === 1
                                            ? ""
                                            : "s"
                                    }`
                                    : "No observations yet"
                            }
                        </div>
                    </div>

                </div>

                <div class="community-observations-list">

                    ${communityHistoryHtml}

                </div>

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
                    communityReviews.length ||
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

                ${
                    riderToolsUrl
                    ?
                    `
                    <br><br>

                    <a
                        class="stop-review-button"
                        href="${riderToolsUrl}"
                        target="_blank"
                        rel="noopener noreferrer">

                        Open WMATA Rider Tools

                    </a>
                    `
                    :
                    ""
                }

            </div>

        `;

    } catch (error) {

        console.error(
            "Failed loading stop profile",
            error
        );

        details.innerHTML =
            "Unable to load stop information.";
    }
}

loadStopProfile();

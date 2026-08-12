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
                    combined.push(`${id} — ${name}`);
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

        const communityReviews =
            Array.isArray(communityData)
                ? communityData
                : communityData.reviews || [];

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
            stop.ddot_interpretation &&
            stop.ddot_interpretation.length
                ? stop.ddot_interpretation
                : [];

        const localEvidenceHtml =
            localEvidence.length
                ? localEvidence.map(item => `
                    <div class="evidence-item">

                        <strong>
                            ${item.public_status || item.source || "Local jurisdiction record"}
                        </strong>

                        <br>

                        ${item.finding || "Finding not recorded"}

                        ${
                            item.confidence
                                ? `
                                    <br>
                                    Confidence:
                                    <strong>${item.confidence}</strong>
                                `
                                : ""
                        }

                        ${
                            item.source_record
                                ? `
                                    <br>
                                    Source record:
                                    ${item.source_record}
                                `
                                : ""
                        }

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
                : "Not recorded";

        const communityBench =
            latestCommunity
                ? amenityValue(latestCommunity.bench)
                : "Not recorded";
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
                ? stop.ddot_interpretation.map(item => `
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
                                ? `
                                    <br>
                                    Source record:
                                    ${item.source_record}
                                `
                                : ""
                        }

                        ${
                            item.routes &&
                            item.routes.length
                                ? `
                                    <br>
                                    Routes:
                                    ${item.routes.join(", ")}
                                `
                                : ""
                        }

                    </div>

                    <br>
                `).join("")
                : "No external evidence available.";

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
                Current amenity information
            </strong>

            <br><br>

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

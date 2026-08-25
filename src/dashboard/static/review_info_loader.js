document.addEventListener("DOMContentLoaded", async () => {
    const stopId = window.location.pathname.split("/").pop();
    const container = document.getElementById("stopInfo");
    if (!container || !stopId) return;

    const amenityLabel = value => ({
        confirmed_yes: "Confirmed present",
        confirmed_no: "Confirmed absent",
        likely_yes: "Likely present",
        likely_no: "Likely absent",
        conflicting: "Sources disagree",
        unknown: "Not enough information"
    })[value] || "Not enough information";

    const observedAmenity = value => ({yes: "Yes", no: "No", unknown: "Unsure"})[
        String(value || "").toLowerCase()
    ] || "Not reported";

    const reviewModeLabel = value => ({
        street_view: "Remote (Street View)",
        other_remote_visual: "Remote (visual source)",
        remote: "Remote",
        in_person: "In person"
    })[value] || "Not recorded";

    const exposureLabel = value => {
        const percentile = Number(value || 0);
        if (percentile >= 90) return "Very high";
        if (percentile >= 75) return "High";
        if (percentile >= 40) return "Moderate";
        return "Lower";
    };

    try {
        const sourceParams = new URLSearchParams(window.location.search);
        const infoParams = new URLSearchParams();
        for (const name of ["assignment_id", "mode", "campaign"]) {
            if (sourceParams.get(name)) infoParams.set(name, sourceParams.get(name));
        }
        const response = await fetch(
            `/review/${stopId}/info${infoParams.toString() ? `?${infoParams}` : ""}`
        );
        const info = await response.json();
        const status = Object.fromEntries(
            (info.amenity_status || []).map(item => [item.amenity_type, item.derived_status])
        );
        const reviews = info.community_reviews?.reviews || [];
        const percentile = info.impact_summary?.rider_exposure_percentile;
        const directions = info.serving_directions || [];
        const headingLabels = [...new Set(directions.map(direction =>
            `${direction.compass_label} (${direction.heading_degrees}°)`
        ))];

        container.innerHTML = `
            <div class="panel review-stop-summary">
                <h2>${info.name || "Bus stop"}</h2>
                <p class="serving-heading"><strong>${headingLabels.length > 1 ? "Serving directions" : "Serving direction"}:</strong> ${headingLabels.length ? headingLabels.join(" · ") : "Not available"}</p>
                <p>${[info.state, info.county, info.municipality].filter(Boolean).join(" · ")}</p>

                ${percentile !== null && percentile !== undefined ? `
                    <div class="rider-exposure-summary">
                        <strong>Rider exposure: ${exposureLabel(percentile)}</strong>
                        (${Number(percentile).toFixed(1)}th percentile)
                        <br><small>Route-based rider exposure, not observed boardings at this stop.</small>
                    </div>` : ""}

                ${info.review_context ? `
                    <div class="evidence-card opportunity-review-context">
                        ${info.review_context.entry_explanation ? `
                            <h3>Why you're reviewing this stop</h3>
                            <p>${info.review_context.entry_explanation}</p>` : ""}
                        <h3>What would be useful to check</h3>
                        <p>${info.review_context.evidence_explanation}</p>
                    </div>` : ""}

                <div class="evidence-card">
                    <h3>What we currently know</h3>
                    ${LocalEvidenceUI.renderCanonicalStatuses(info.amenity_status)}
                    <p><small>Likely and conflicting records still need current verification.</small></p>
                </div>

                ${info.amenity_evidence?.length ? `
                    <div class="evidence-card">
                        <h3>Local jurisdiction evidence</h3>
                        <p>Supporting local records are shown separately from community observations.</p>
                        ${LocalEvidenceUI.render(info.amenity_evidence)}
                    </div>` : ""}

                <div class="evidence-card">
                    <h3>Community observations</h3>
                    ${reviews.length ? reviews.map(review => `
                        <div class="community-observation">
                            <strong>${review.date || "Date not recorded"}</strong><br>
                            Shelter: ${observedAmenity(review.shelter)}<br>
                            Bench: ${observedAmenity(review.bench)}<br>
                            Review method: ${reviewModeLabel(review.review_mode)}
                            ${review.streetview_imagery_month ? `<br>Imagery captured: ${review.streetview_imagery_month}` : ""}
                            ${review.preliminary_clearance ? `<br>Preliminary visual space observation: ${review.preliminary_clearance}` : ""}
                            ${review.notes?.trim() ? `<br>Notes: ${review.notes}` : ""}
                        </div>`).join("") : `
                        <p>No community observations yet. Your review can create a dated record for this stop.</p>`}
                </div>

                <details>
                    <summary>Stop reference details</summary>
                    <p>Internal physical stop ID: ${info.stop_id}<br>
                    External stop ID: ${info.external_stop_id || "Not recorded"}<br>
                    Coordinates: ${Number(info.lat).toFixed(5)}, ${Number(info.lon).toFixed(5)}</p>
                </details>

                <p><small>This is a preliminary visual check of the available waiting space.</small></p>

                <div class="review-reference-links">
                    ${info.streetview_url ? `<a href="${info.streetview_url}" target="_blank" rel="noopener noreferrer" class="stop-review-button">Open Google Street View</a>` : ""}
                    ${info.wmata_rider_tools_url ? `<a href="${info.wmata_rider_tools_url}" target="_blank" rel="noopener noreferrer" class="stop-review-button">Open WMATA Rider Tools</a>` : ""}
                </div>
            </div>`;

        document.dispatchEvent(new CustomEvent("review-context-loaded", {
            detail: info.review_context || {}
        }));
    } catch (error) {
        console.error("Failed loading stop info", error);
        container.textContent = "Unable to load stop information.";
    }
});

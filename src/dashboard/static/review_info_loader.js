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

    const headingLabel = value => {
        const degrees = Number(value);
        if (!Number.isFinite(degrees)) return String(value);
        const directions = [
            "Northbound", "Northeast", "Eastbound", "Southeast",
            "Southbound", "Southwest", "Westbound", "Northwest"
        ];
        const normalized = ((degrees % 360) + 360) % 360;
        return `${directions[Math.round(normalized / 45) % 8]} (${value}°)`;
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
        const sourceLabel = value => ({
            DDOT_ARCGIS: "DDOT shelter inventory",
            ALEXANDRIA: "City of Alexandria inventory",
            MONTGOMERY_COUNTY_WMATA: "Montgomery County inventory",
            FAIRFAX_COUNTY: "Fairfax County inventory",
            PRINCE_GEORGES_COUNTY_THEBUS: "Prince George's County TheBus inventory",
            FALLS_CHURCH_CITY: "City of Falls Church inventory",
            OPENSTREETMAP: "OpenStreetMap",
            COMMUNITY: "Community observations"
        })[value] || String(value || "Evidence source").replaceAll("_", " ");
        const conflicts = (info.amenity_status || []).filter(item =>
            item.derived_status === "conflicting" ||
            item.consensus_conflicts_with_other_evidence
        );
        const headings = info.serving_headings || [];

        container.innerHTML = `
            <div class="panel review-stop-summary">
                <h2>${info.name || "Bus stop"}</h2>
                ${headings.length ? `<p class="serving-heading"><strong>Serving heading${headings.length > 1 ? "s" : ""}:</strong> ${headings.map(headingLabel).join(" · ")}</p>` : ""}
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
                    <p>Shelter: <strong>${amenityLabel(status.shelter)}</strong><br>
                    Bench: <strong>${amenityLabel(status.bench)}</strong></p>
                    <p><small>Likely and conflicting records still need current verification.</small></p>
                </div>

                ${conflicts.length ? `
                    <div class="evidence-card evidence-conflict-comparison">
                        <h3>Where the evidence disagrees</h3>
                        ${conflicts.map(conflict => `
                            <div class="conflict-amenity">
                                <strong>${conflict.amenity_type === "bench" ? "Bench" : "Shelter"}</strong>
                                ${(conflict.conflict_evidence || []).map(claim => `
                                    <div>${sourceLabel(claim.source)}: <strong>${claim.claim === "present" ? "Present" : "Absent"}</strong>${claim.count ? ` (${claim.count} observation${claim.count === 1 ? "" : "s"})` : ""}</div>
                                `).join("")}
                            </div>`).join("")}
                        <p><small>These records describe a disagreement; they do not establish that one source is wrong.</small></p>
                    </div>` : ""}

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

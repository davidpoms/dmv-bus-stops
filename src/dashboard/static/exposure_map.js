/* Uses the existing Leaflet map and shared request generation to prevent stale layers. */
function exposureText(value) {
    const span = document.createElement("span");
    span.textContent = String(value ?? "");
    return span.innerHTML;
}

let exposureGeographies = [];

function exposureGeographyParams(prefix) {
    const kind = document.getElementById(`${prefix}GeographyType`)?.value;
    const value = document.getElementById(`${prefix}GeographyValue`)?.value;
    if (!kind) return {};
    return value ? {geography_type: kind, geography_value: value} : null;
}

function exposureComparisonText(comparison) {
    if (!comparison) return "";
    const name = comparison.geography_value || "Entire DMV";
    return `${name}: ${comparison.usable_population.toLocaleString()} stops with exposure, ` +
        `${comparison.population.toLocaleString()} active stops.` +
        (comparison.small_population ? " Fewer than 20 usable stops; ranks are shown without percentile bands." : "");
}

function updateExposureGeography(prefix) {
    const kind = document.getElementById(`${prefix}GeographyType`).value;
    const select = document.getElementById(`${prefix}GeographyValue`);
    const label = document.getElementById(`${prefix}GeographyLabel`);
    select.replaceChildren(new Option("Choose a jurisdiction", ""));
    const group = exposureGeographies.find(g => g.type === kind);
    if (group) group.values.forEach(v => select.add(new Option(`${v.value} (${v.population} active stops)`, v.value)));
    select.hidden = label.hidden = !kind;
    label.textContent = group?.label || "Jurisdiction";
    if (prefix === "exposure") loadStops(); else loadBenchCandidates();
}

async function loadExposureGeographies() {
    try {
        const response = await fetch("/map/exposure?limit=1");
        if (!response.ok) throw new Error("Geographies unavailable");
        exposureGeographies = (await response.json()).geographies;
        for (const prefix of ["exposure", "seating"]) {
            const selector = document.getElementById(`${prefix}GeographyType`);
            exposureGeographies.forEach(g => selector.add(new Option(g.label, g.type)));
        }
    } catch (error) {
        document.getElementById("seatingExposureContext").textContent = "Jurisdiction choices unavailable; Entire DMV is still available.";
    }
}

async function loadExposureMap() {
    const version = ++mapRequestVersion;
    const mode = document.getElementById("exposureMode").value;
    const selector = document.getElementById("exposureRoute");
    const status = document.getElementById("exposureStatus");
    markers.forEach(marker => map.removeLayer(marker));
    markers = [];
    const geography = exposureGeographyParams("exposure");
    if (geography === null) {
        status.textContent = "Choose a jurisdiction to compare within.";
        return;
    }
    status.textContent = "Loading rider exposure…";
    try {
        const params = new URLSearchParams({mode, route: selector.value, ...geography});
        const response = await fetch(`/map/exposure?${params}`);
        if (!response.ok) throw new Error("Exposure unavailable");
        const data = await response.json();
        if (version !== mapRequestVersion) return;
        if (selector.options.length === 1) {
            data.routes.forEach(route => {
                selector.add(new Option(`${route.route_id} — ${route.route_name || "Route"}`, route.route_id));
            });
        }
        const context = data.selected_route;
        status.textContent = mode === "route" && !context ? "Choose a route to see its active stops." :
            `${context ? context.route_id + " — " + (context.route_name || "") + ": " : "Highest exposure: "}` +
            `${data.stops.length} of ${data.total_matching} active stops shown` +
            `${data.truncated ? " (top 100 by exposure)" : ""}. Recorded month: ${data.source_period || "unavailable"}. ` +
            exposureComparisonText(data.comparison);
        const labels = {confirmed_yes: "Confirmed present", likely_yes: "Likely present",
            confirmed_no: "Confirmed absent", likely_no: "Likely absent",
            conflicting: "Sources disagree", unknown: "Unknown — needs verification"};
        data.stops.forEach(stop => {
            const marker = L.circleMarker([stop.latitude, stop.longitude], {
                radius: 5 + 7 * (stop.exposure_percentile || 0) / 100,
                color: "#175b83", fillColor: "#287fb0", fillOpacity: 0.65, weight: 2
            }).addTo(map);
            const id = Number(stop.physical_stop_id);
            const local = data.comparison.geography_value;
            const rankText = local && stop.jurisdiction_rank ?
                `<br>Rank #${stop.jurisdiction_rank} of ${stop.jurisdiction_usable_population} stops with exposure` : "";
            const popup = document.createElement("div");
            popup.className = "exposure-popup";
            popup.innerHTML = `<strong>${exposureText(stop.stop_name || "Unnamed stop")}</strong>
                <p>Rider exposure: <strong>${exposureText(stop.exposure_band)}</strong>${local ? " in " + exposureText(local) : " in DMV"}${rankText}
                ${local ? `<br><small>DMV exposure: ${exposureText(stop.regional_band)}</small>` : ""}</p>
                <p>${exposureText(stop.ridership_label)}: ${stop.ridership_value == null ? "Unavailable" : Number(stop.ridership_value).toLocaleString(undefined, {maximumFractionDigits: 0})}
                <br><small>Monthly weekday total ÷ ${stop.weekday_divisor || "unknown"} calendar weekdays.
                Not observed boarding activity at this stop.</small></p>
                <p>${stop.active_route_count} routes — ${exposureText(stop.connection_class)}<br>
                ${stop.active_routes.map(r => exposureText(r.route_id)).join(", ")}</p>
                <p>Bench: ${exposureText(labels[stop.bench_status] || labels.unknown)}<br>
                Shelter: ${exposureText(labels[stop.shelter_status] || labels.unknown)}</p>
                <a href="/stop/${id}">View stop</a> · <a href="/review/${id}">Review stop</a>`;
            marker.bindPopup(popup, {
                maxWidth: Math.max(100, Math.min(270, map.getSize().x - 60)),
                minWidth: 100, maxHeight: Math.min(300, window.innerHeight * 0.4)
            });
            marker.bindTooltip(`${stop.stop_name || "Unnamed stop"}: ${stop.exposure_band}`.replace(/</g, "&lt;"));
            markers.push(marker);
        });
        if (markers.length) map.fitBounds(L.featureGroup(markers).getBounds(), {padding: [24, 24], maxZoom: 15, animate: false});
    } catch (error) {
        if (version === mapRequestVersion) status.textContent = "Rider exposure is unavailable. Try again or switch Off.";
    }
}

document.getElementById("exposureMode").addEventListener("change", event => {
    const routeMode = event.target.value === "route";
    document.getElementById("exposureDetails").hidden = event.target.value === "off";
    map.zoomControl.setPosition(event.target.value === "off" ? "topleft" : "bottomright");
    document.getElementById("exposureRoute").hidden = !routeMode;
    document.getElementById("exposureRouteLabel").hidden = !routeMode;
    document.getElementById("exposureLegend").hidden = event.target.value === "off";
    document.getElementById("exposureStatus").textContent = "";
    loadStops();
});
document.getElementById("exposureRoute").addEventListener("change", loadExposureMap);
for (const prefix of ["exposure", "seating"]) {
    document.getElementById(`${prefix}GeographyType`).addEventListener("change", () => updateExposureGeography(prefix));
    document.getElementById(`${prefix}GeographyValue`).addEventListener("change", () => {
        if (prefix === "exposure") loadStops(); else loadBenchCandidates();
    });
}
window.addEventListener("load", loadExposureGeographies);

(function (root, factory) {
    const api = factory();

    if (typeof module === "object" && module.exports) {
        module.exports = api;
    }

    root.LocalEvidenceUI = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
    const AMENITY_LABELS = {
        shelter: "Shelter",
        bench: "Bench",
        trash_can: "Trash can",
        sign: "Sign",
        ada_bus_pad: "ADA bus pad",
        ada_path: "ADA path",
        recycling: "Recycling",
        bikerack: "Bike rack",
        parking: "Parking",
        streetlight: "Streetlight",
        real_time_sign: "Real-time sign",
        bus_bay: "Bus bay",
        bus_bulb: "Bus bulb"
    };

    const AMENITY_ORDER = [
        "shelter",
        "bench",
        "trash_can",
        "recycling",
        "sign",
        "real_time_sign",
        "ada_bus_pad",
        "ada_path",
        "bus_bay",
        "bus_bulb",
        "bikerack",
        "parking",
        "streetlight"
    ];

    const JURISDICTION_LABELS = {
        DISTRICT_OF_COLUMBIA: "District of Columbia",
        PRINCE_GEORGES_COUNTY: "Prince George's County",
        MONTGOMERY_COUNTY: "Montgomery County",
        ARLINGTON_COUNTY: "Arlington County",
        ALEXANDRIA: "City of Alexandria",
        FAIRFAX_COUNTY: "Fairfax County"
    };

    const SOURCE_LABELS = {
        PRINCE_GEORGES_COUNTY_THEBUS:
            "Prince George's County TheBus stop inventory",
        DDOT_ARCGIS: "DDOT shelter asset record"
    };

    function escapeHtml(value) {
        return String(value)
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#39;");
    }

    function genericLabel(value) {
        return String(value || "Amenity")
            .replace(/[_-]+/g, " ")
            .trim()
            .toLowerCase()
            .replace(/^\w/, character => character.toUpperCase());
    }

    function amenityLabel(type) {
        return AMENITY_LABELS[type] || genericLabel(type);
    }

    function evidenceValue(evidence) {
        const value = String(evidence.value ?? "").trim().toLowerCase();

        if (value === "yes") return "Yes";
        if (value === "no") return "No";
        if (evidence.present === 1 || evidence.present === true ||
            evidence.present === "1") return "Yes";
        if (evidence.present === 0 || evidence.present === false ||
            evidence.present === "0") return "No";
        return "Not recorded";
    }

    function amenityRank(type) {
        const rank = AMENITY_ORDER.indexOf(type);
        return rank === -1 ? AMENITY_ORDER.length : rank;
    }

    function compareAmenities(left, right) {
        const rankDifference =
            amenityRank(left.amenity_type) - amenityRank(right.amenity_type);
        return rankDifference || String(left.amenity_type || "")
            .localeCompare(String(right.amenity_type || ""));
    }

    function friendlyJurisdiction(evidence) {
        const internal = evidence.jurisdiction || evidence.source;
        return JURISDICTION_LABELS[internal] || genericLabel(internal || "Local jurisdiction");
    }

    function friendlySource(source) {
        return SOURCE_LABELS[source] || null;
    }

    function groupEvidence(records) {
        const groups = new Map();

        (Array.isArray(records) ? records : [])
            .filter(evidence => evidence && evidence.source !== "DDOT")
            .forEach(evidence => {
                const key = [
                    evidence.jurisdiction || "",
                    evidence.source || "",
                    evidence.source_record || ""
                ].join("|");

                if (!groups.has(key)) {
                    groups.set(key, {
                        jurisdiction: friendlyJurisdiction(evidence),
                        source: evidence.source || null,
                        sourceLabel: friendlySource(evidence.source),
                        sourceRecord: evidence.source_record || null,
                        amenities: []
                    });
                }

                groups.get(key).amenities.push(evidence);
            });

        return Array.from(groups.values())
            .map(group => ({
                ...group,
                amenities: group.amenities.sort(compareAmenities)
            }))
            .sort((left, right) =>
                left.jurisdiction.localeCompare(right.jurisdiction) ||
                String(left.source || "").localeCompare(String(right.source || "")) ||
                String(left.sourceRecord || "").localeCompare(String(right.sourceRecord || ""))
            );
    }

    function render(records, options = {}) {
        const groups = groupEvidence(records);

        if (!groups.length) {
            return options.showEmpty
                ? `<div class="community-observations-empty">No current local jurisdiction amenity record available.</div>`
                : "";
        }

        return groups.map(group => `
            <div class="evidence-item">
                <strong>${escapeHtml(group.jurisdiction)}</strong>
                ${group.sourceLabel ? `<br>Source: <strong>${escapeHtml(group.sourceLabel)}</strong>` : ""}
                <br><br>
                ${group.amenities.map(evidence => `
                    ${escapeHtml(amenityLabel(evidence.amenity_type))}:
                    <strong>${evidenceValue(evidence)}</strong><br>
                `).join("")}
                Source record:
                ${escapeHtml(group.sourceRecord || "Not recorded")}
            </div>
        `).join("");
    }

    return {
        AMENITY_LABELS,
        AMENITY_ORDER,
        evidenceValue,
        groupEvidence,
        amenityLabel,
        render
    };
});

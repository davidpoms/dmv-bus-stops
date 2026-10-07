/* Only trusted layout markup enters the HTML parser. Values are inserted afterward. */
window.SafeRender = {
    create() {
        const nodes = [];
        function slot(node) {
            const index = nodes.push(node) - 1;
            return `<span data-safe-render-slot="${index}"></span>`;
        }
        function text(value) {
            return slot(document.createTextNode(String(value ?? "")));
        }
        function link(url, label, className = "", external = false) {
            let parsed;
            try {
                parsed = new URL(url, window.location.href);
                if (!["http:", "https:"].includes(parsed.protocol)) return text(label);
            } catch (_) {
                return text(label);
            }
            const anchor = document.createElement("a");
            anchor.href = parsed.href;
            anchor.textContent = label;
            anchor.className = className;
            if (external) {
                anchor.target = "_blank";
                anchor.rel = "noopener noreferrer";
            }
            return slot(anchor);
        }
        function mount(container, markup) {
            container.innerHTML = markup;
            container.querySelectorAll("[data-safe-render-slot]").forEach(placeholder => {
                // Clone because trusted layout may reuse a generated slot.
                placeholder.replaceWith(nodes[Number(placeholder.dataset.safeRenderSlot)].cloneNode(true));
            });
        }
        function html(markup) {
            const container = document.createElement("div");
            mount(container, markup);
            return container.innerHTML;
        }
        return {text, link, mount, html};
    },
    borderJurisdiction(info, stopId, render) {
        const overlay = info.operational_jurisdiction;
        if (!overlay) return "";
        const resolved = overlay.jurisdiction_basis === "border_centerline_convention"
            && ["DC", "MD"].includes(overlay.value);
        const title = resolved
            ? `Likely jurisdiction: ${overlay.value === "DC" ? "District of Columbia" : "Maryland"}`
            : "Jurisdiction needs confirmation";
        const notice = resolved
            ? "This stop is near the DC–Maryland boundary and is classified using the project's border-road convention. If this appears incorrect, please let us know."
            : "This stop is near the DC–Maryland boundary and could not be reliably classified using the available evidence. If you know whether this stop is in DC or Maryland, please let us know.";
        const feedback = `/feedback?stop_id=${encodeURIComponent(stopId)}&page=${encodeURIComponent(`/stop/${stopId}`)}`;
        return `<div class="border-jurisdiction-notice">
            <strong>${render.text(title)}</strong>
            <p>${render.text(notice)}</p>
            <p>This is a project convention, not a legal boundary determination or evidence of ownership or maintenance responsibility.</p>
            ${resolved && overlay.border_review_required ? "<p>Border evidence needs review; the jurisdiction shown remains a nominal result.</p>" : ""}
            <p>Stored geography: ${render.text([info.state, info.county, info.municipality].filter(Boolean).join(" · ") || "Not recorded")}</p>
            ${render.link(feedback, "Report a stop-location concern", "dashboard-button")}
        </div>`;
    },
    exposure(value, unavailable = "Unknown", round = false) {
        return value == null ? unavailable : (round ? Math.round(value) : value).toLocaleString();
    }
};

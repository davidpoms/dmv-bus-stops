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
    exposure(value, unavailable = "Unknown", round = false) {
        return value == null ? unavailable : (round ? Math.round(value) : value).toLocaleString();
    }
};

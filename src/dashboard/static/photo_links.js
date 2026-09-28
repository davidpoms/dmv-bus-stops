window.PhotoLinks = {
    render(attachments) {
        const container = document.createElement("span");
        for (const attachment of attachments || []) {
            try {
                const url = new URL(attachment.external_url);
                if (!["http:", "https:"].includes(url.protocol)) continue;
                const link = document.createElement("a");
                link.href = url.href;
                link.target = "_blank";
                link.rel = "noopener noreferrer";
                link.textContent = "View photos";
                link.className = "stop-review-button";
                container.append(link, document.createTextNode(" "));
            } catch (_) { /* Ignore malformed historical references. */ }
        }
        return container.innerHTML;
    }
};

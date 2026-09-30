/* All renderer targets are inert documents: fixture markup cannot run or load URLs. */
(async () => {
    const results = {};
    const fixtures = ['<img src=x onerror=alert(1)>', '<script>marker</script>',
        '<b>reviewer</b>', '& " \' < >', '<span data-safe-render-slot="999">'];
    function assert(value, message) { if (!value) throw new Error(message); }
    async function test(name, run) {
        try { await run(); results[name] = 'ok'; }
        catch (error) { results[name] = String(error.stack || error); }
    }
    function environment() {
        const doc = document.implementation.createHTMLDocument('inert renderer fixture');
        assert(doc.defaultView === null, 'Renderer fixture must be inert');
        const win = {location: {href: 'https://example.test/review/42', pathname: '/review/42', search: ''}};
        new Function('window', 'document', sources['safe_render.js'])(win, doc);
        new Function('window', 'document', sources['photo_links.js'])(win, doc);
        new Function('globalThis', 'document', 'SafeRender', sources['local_evidence.js'])(win, doc, win.SafeRender);
        return {doc, win};
    }
    function safeMarkup(root) {
        assert(!root.querySelector('img, script, b, [onerror], [data-safe-render-slot]'), 'Untrusted markup or unresolved slot');
        assert(root.querySelector('strong'), 'Trusted strong markup missing');
    }
    function literal(root, value) {
        const walker = root.ownerDocument.createTreeWalker(root, NodeFilter.SHOW_TEXT);
        let found = false;
        while (walker.nextNode()) if (walker.currentNode.data.includes(value)) found = true;
        assert(found, 'Literal missing: ' + value);
    }
    function data(value = 'Ordinary note', exposure = 1200) {
        return {
            stop_id: 42, external_stop_id: value, location: value, name: value,
            lat: 38.9, lon: -77.1, routes: [value],
            impact_summary: {routes: [value], routes_served: 1, estimated_weekday_boardings: exposure},
            community_reviews: {review_count: 1, reviews: [{notes: value, date: value,
                streetview_imagery_month: value, preliminary_clearance: value}]},
            serving_directions: [{compass_label: value, heading_degrees: 90}],
            state: value, county: value, municipality: value,
            review_context: {entry_explanation: value, evidence_explanation: value},
            recommendations: [{priority: value, confidence: value, reasons: [value]}],
            amenity_status: [], amenity_evidence: []
        };
    }
    async function stopPage(info, retired = false) {
        const env = environment();
        env.doc.body.innerHTML = '<h1 id="name"></h1><div id="details"></div>';
        const fetch = async url => ({ok: true, status: retired ? 410 : 200,
            json: async () => url.endsWith('community-reviews') ? info.community_reviews.reviews : info});
        const source = sources['stop_detail.js'].replace(/loadStopProfile\(\);\s*$/, 'return loadStopProfile();');
        await new Function('document', 'fetch', 'stopId', 'SafeRender', 'LocalEvidenceUI', 'PhotoLinks', source)(
            env.doc, fetch, 42, env.win.SafeRender, env.win.LocalEvidenceUI, env.win.PhotoLinks);
        assert(env.doc.body.querySelector('.card'), 'Stop render failed');
        return env;
    }
    async function reviewPage(info) {
        const env = environment();
        env.doc.body.innerHTML = '<div id="stopInfo"></div>';
        let callback;
        env.doc.addEventListener = (name, handler) => { if (name === 'DOMContentLoaded') callback = handler; };
        await new Function('document', 'window', 'fetch', 'SafeRender', 'LocalEvidenceUI', 'PhotoLinks', sources['review_info_loader.js'])(
            env.doc, env.win, async () => ({json: async () => info}), env.win.SafeRender, env.win.LocalEvidenceUI, env.win.PhotoLinks);
        await callback();
        assert(env.doc.querySelector('.review-stop-summary'), 'Review render failed');
        return env;
    }
    function completion(value, exposure) {
        const env = environment();
        const source = sources['review.html'];
        const successfulResponse = source.indexOf('if(!response.ok)');
        const currentStart = source.indexOf('const render = SafeRender.create();', successfulResponse);
        const start = currentStart >= 0 ? currentStart : source.indexOf('document.body.innerHTML = `', successfulResponse);
        assert(start >= 0, 'Completion renderer missing');
        const end = source.indexOf('\n\n\n});', start);
        assert(end > start, 'Completion boundary missing');
        new Function('document', 'SafeRender', 'result', 'stopId', source.slice(start, end))(
            env.doc, env.win.SafeRender, {community_impact: {average_weekday_boardings: exposure, routes: [value]},
                reviewer_stats: {display_name: value, review_count: value, stops_reviewed: value,
                    stewarded_stops: value, routes_covered: [value],
                    average_weekday_route_exposure_represented: exposure,
                    route_exposure_coverage: {complete: false, stops_with_exposure: value, reviewed_stops: value}}}, 42);
        return env;
    }
    await test('text', () => {
        const {doc, win} = environment();
        for (const value of fixtures) {
            const render = win.SafeRender.create();
            const token = render.text(value);
            assert(!token.includes(value), 'Value reached HTML parser');
            render.mount(doc.body, `<strong>${token}</strong><p>${token}</p>`);
            safeMarkup(doc.body);
            assert(doc.querySelector('strong').textContent === value, 'Text changed');
            assert(doc.querySelector('p').textContent === value, 'Reused slot lost text');
        }
    });
    await test('stop', async () => {
        for (const value of fixtures) {
            const {doc} = await stopPage(data(value));
            safeMarkup(doc.body);
            assert(doc.getElementById('name').textContent === value, 'Name changed');
            literal(doc.querySelector('.community-observation-notes'), value);
            literal(doc.querySelector('.community-observation-provenance'), value);
            if (Number.isNaN(new Date(value).getTime())) {
                literal(doc.querySelector('.community-observation-date'), value);
            }
            literal(doc.querySelector('.recommendation-reasons'), value);
            literal(doc.querySelector('#details > .card'), value);
        }
    });
    await test('review', async () => {
        for (const value of fixtures) {
            const {doc} = await reviewPage(data(value));
            safeMarkup(doc.body);
            assert(doc.querySelector('h2').textContent === value, 'Review name changed');
            literal(doc.querySelector('.serving-heading'), value);
            literal(doc.querySelector('.community-observation'), value);
            literal(doc.querySelector('.opportunity-review-context'), value);
        }
    });
    await test('completion', () => {
        for (const value of fixtures) {
            const {doc} = completion(value, 0);
            safeMarkup(doc.body);
            literal(doc.querySelector('.completion-card > p'), value);
            literal(doc.querySelector('.current-review'), value);
            assert(doc.querySelectorAll('a.dashboard-button').length === 5, 'Completion actions missing');
        }
    });
    await test('evidence', () => {
        const {doc, win} = environment();
        for (const value of fixtures) {
            doc.body.innerHTML = win.LocalEvidenceUI.renderCanonicalStatuses([{amenity_type: value,
                derived_status: 'likely_yes', contributing_evidence: [{source: value, claim: value,
                    count: value, source_record: value}]}]) + win.LocalEvidenceUI.render([
                {source: value, jurisdiction: value, source_record: value, amenity_type: value, value: 'yes'}]);
            safeMarkup(doc.body);
            literal(doc.querySelector('.canonical-amenity-conclusion'), value);
            literal(doc.querySelector('.evidence-item'), value);
            assert(doc.body.textContent.includes('likely present'), 'Evidence meaning changed');
        }
    });
    await test('photos', () => {
        const {doc, win} = environment();
        const url = 'https://photos.example/test?label="<b>reviewer</b>&x=1';
        doc.body.innerHTML = win.PhotoLinks.render([{external_url: url},
            {external_url: 'javascript:marker'}, {external_url: 'data:text/html,marker'}, {external_url: 'not a URL'}]);
        assert(doc.querySelectorAll('a').length === 1, 'Unsafe URL accepted');
        const link = doc.querySelector('a');
        assert(link.href === new URL(url).href, 'Photo URL changed');
        assert(link.textContent === 'View photos', 'Photo label changed');
        assert(link.target === '_blank' && link.rel === 'noopener noreferrer', 'Unsafe link attributes');
        assert(!doc.querySelector('b'), 'URL interpreted as markup');
    });
    await test('links', async () => {
        const info = data(); info.streetview_url = 'javascript:marker'; info.wmata_rider_tools_url = 'data:text/html,marker';
        for (const env of [await stopPage(info), await reviewPage(info)]) {
            const links = [...env.doc.querySelectorAll('a')];
            assert(links.every(link => ['https:', 'http:'].includes(link.protocol)), 'Unsafe reference href');
            const maps = links.find(link => link.textContent === 'Open in Google Maps');
            assert(new URL(maps.href).searchParams.get('query') === '38.9,-77.1', 'Map coordinates changed');
            assert(maps.rel === 'noopener noreferrer', 'Map link unsafe');
        }
    });
    await test('retired', async () => {
        for (const value of fixtures) {
            const {doc} = await stopPage({identity_status: 'retired', message: value,
                successors: [{stop_id: value, url: 'javascript:marker'}, {stop_id: 43, url: '/stop/43'}]}, true);
            safeMarkup(doc.body); literal(doc.querySelector('.retired-stop-message'), value);
            assert(doc.querySelectorAll('a').length === 1, 'Unsafe successor link');
            assert(doc.querySelector('a').pathname === '/stop/43', 'Valid successor lost');
        }
    });
    await test('normal', async () => {
        const value = '  Ordinary notes & "quotes"\nnext line  ';
        for (const env of [await stopPage(data(value)), await reviewPage(data(value)), completion(value, 5)]) {
            literal(env.doc.body, value);
        }
    });
    await test('exposure', () => {
        const {win} = environment();
        for (const [value, expected] of [[1200, (1200).toLocaleString()], [0, '0'], [null, 'Unknown'], [undefined, 'Unknown']]) {
            assert(win.SafeRender.exposure(value) === expected, 'Formatter mismatch');
        }
    });
    await test('stop_exposure', async () => {
        for (const value of [1200, 0, null, undefined]) {
            const info = data(); info.impact_summary.estimated_weekday_boardings = value;
            const {doc} = await stopPage(info);
            const expected = value == null ? 'Unknown' : value.toLocaleString();
            assert(doc.querySelector('.amenity-comparison-row span strong').textContent.trim() === expected, 'Stop exposure mismatch');
        }
    });
    await test('completion_exposure', () => {
        for (const value of [1200.6, 0, null, undefined]) {
            const {doc} = completion('Reviewer', value);
            const expected = value == null ? 'unknown' : Math.round(value).toLocaleString();
            assert(doc.querySelector('.current-review strong').textContent.trim() === expected, 'Completion exposure mismatch');
        }
    });
    // Encode results, not fixture markup, into the only active document.
    document.getElementById('results').textContent = [...new TextEncoder().encode(JSON.stringify(results))]
        .map(byte => byte.toString(16).padStart(2, '0')).join('');
})();

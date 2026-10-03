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
    function progressData(count = 0, title = null) {
        return {distinct_stops_documented: count,
            explorer: {crossed_thresholds: count ? [5, 20] : [], next_threshold: count ? 50 : 5,
                remaining: count ? 30 : 5},
            first_looks: {available: true, count: count ? 3 : 0},
            featured_geography: title === null ? null : {display_title: title,
                numerator: 7, denominator: 40, current_percentage: 17.5,
                next_tier_percentage: 25, required_count: 10, remaining: 3},
            reviewer_id: 'PRIVATE_ID', reviewer_key: 'PRIVATE_KEY',
            stops: ['PRIVATE_STOP'], coordinates: 'PRIVATE_COORDINATES',
            geographies: [{display_title: 'UNSELECTED_GEOGRAPHY'}]};
    }
    function activityData(name = 'Main Street Stop') {
        return {available: true, activities: Array.from({length: 5}, (_, i) => ({
            stop_id: 9001 + i, stop_name: name,
            completed_at: `2026-10-01T12:0${4-i}:00Z`
        }))};
    }
    async function progressPage(page, signedIn, payload, status = 200, authStatus = 200, activityResponse = null, achievementsResponse = null) {
        const {doc} = environment();
        const template = sources[page + '.html'];
        doc.documentElement.innerHTML = template.replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, '');
        const calls = [];
        const handlers = {};
        const state = {signedIn, progress: null, activity: activityResponse, achievements: achievementsResponse, visibility: 'visible', authStatus};
        Object.defineProperty(doc, 'visibilityState', {get: () => state.visibility});
        doc.addEventListener = (name, handler) => { handlers[name] = handler; };
        const win = {addEventListener: (name, handler) => { handlers[name] = handler; },
            location: {assign: () => {}}};
        const fetch = async url => {
            calls.push(url);
            if (url === '/api/reviewer/achievements') {
                return state.achievements ? state.achievements() :
                    {ok: true, status: 200, json: async () => ({available: true, achievements: []})};
            }
            if (url === '/api/reviewer/recent-activity') {
                if (state.activity) return state.activity();
                return {ok: true, status: 200, json: async () => activityData()};
            }
            if (url === '/api/reviewer/progress') {
                if (state.progress) return state.progress();
                if (status === 'network') throw new Error('Offline');
                return {ok: status === 200, status, json: async () => payload};
            }
            return {ok: state.authStatus === 200, status: state.authStatus, json: async () => ({
                signed_in: state.signedIn, display_name: 'Existing reviewer',
                stats: {reviews_completed: 12, stops_reviewed: 9, stewarded_stops: 0},
                stewarded_stops: []})};
        };
        let source;
        if (page === 'reviewer_profile') {
            source = template.match(/<script>([\s\S]*?)<\/script>/)[1]
                .replace(/loadProfile\(\);\s*$/, 'return loadProfile();');
        } else {
            const full = sources['dashboard.js'];
            source = full.slice(full.indexOf('let communityProgressVersion ='),
                full.indexOf('let benchCandidateRows ='))
                + '\nreturn loadCommunityProfileCard();';
        }
        try { await new Function('document', 'fetch', 'window', source)(doc, fetch, win); }
        catch (error) { assert(authStatus !== 200, 'Unexpected profile failure: ' + error); }
        // Profile progress loads independently of the existing activity renderer.
        for (let i = 0; i < 12; i++) await Promise.resolve();
        const card = doc.getElementById(page === 'dashboard' ? 'communityProfileCard' : 'privateProgressCard');
        const content = doc.getElementById(page === 'dashboard' ? 'communityProgressContent' : 'privateProgressContent');
        return {doc, calls, card, content, state, handlers};
    }
    await test('progress_auth', async () => {
        for (const page of ['reviewer_profile', 'dashboard']) {
            for (const authStatus of [200, 401, 403, 503]) {
                const env = await progressPage(page, false, progressData(), 200, authStatus);
                assert(env.calls.length === 1, 'Signed-out request fetched progress');
                assert(env.card.style.display === 'none', 'Signed-out progress visible');
            }
            for (const status of [401, 403, 503, 'network']) {
                const env = await progressPage(page, true, progressData(20), status);
                assert(env.calls[1] === '/api/reviewer/progress', 'Missing authenticated progress fetch');
                assert(!env.content.textContent.includes('20'), 'Private data rendered after failure');
                if (page === 'reviewer_profile') {
                    literal(env.doc.getElementById('stats'), '12');
                    assert(env.doc.getElementById('profileName').textContent === 'Existing reviewer', 'Profile lost');
                } else {
                    assert(env.card.style.display !== 'none', 'Profile navigation hidden by progress failure');
                    assert(env.doc.querySelector('#communityProfileCard a').getAttribute('href') === '/reviewer/profile', 'Profile navigation lost');
                    assert(env.doc.getElementById('map'), 'Dashboard map lost');
                }
            }
        }
    });
    await test('progress_content', async () => {
        new Function(sources['dashboard.js']);
        for (const page of ['reviewer_profile', 'dashboard']) {
            const zero = await progressPage(page, true, progressData());
            assert(zero.card.style.display !== 'none', 'Signed-in progress hidden');
            literal(zero.content, '0');
            literal(zero.content, 'provisional');
            if (page === 'reviewer_profile') literal(zero.content, '5 stops (5 remaining)');
            for (const value of fixtures) {
                const env = await progressPage(page, true, progressData(20, value));
                literal(env.content, value);
                assert(!env.content.querySelector('img, script, b, [onerror]'), 'Progress interpreted as markup');
                assert(!/PRIVATE_|UNSELECTED_GEOGRAPHY/.test(env.content.textContent), 'Non-display data exposed');
                if (page === 'reviewer_profile') {
                    literal(env.content, '5, 20');
                    literal(env.content, '50 stops (30 remaining)');
                    literal(env.content, '7 / 40 stops (17.5%)');
                    literal(env.content, '10 stops (3 remaining)');
                } else {
                    assert(!env.content.textContent.includes('17.5'), 'Full geography leaked into teaser');
                }
            }
        }
    });
    await test('progress_restoration', async () => {
        for (const page of ['reviewer_profile', 'dashboard']) {
            const env = await progressPage(page, true, progressData(20, 'Private geography'));
            literal(env.content, 'Private geography');
            const initialCalls = env.calls.length;
            await env.handlers.pageshow({persisted: false});
            assert(env.calls.length === initialCalls, 'Initial pageshow duplicated loading');
            env.handlers.pagehide();
            assert(env.content.textContent === '', 'Page exit retained private progress');
            await env.handlers.pageshow({persisted: true});
            literal(env.content, 'Private geography');
            env.state.signedIn = false;
            env.handlers.pagehide();
            const restored = env.handlers.pageshow({persisted: true});
            assert(!env.content.textContent.includes('Private geography'), 'Restoration left old progress visible');
            const before = env.calls.filter(url => url === '/api/reviewer/progress').length;
            await restored;
            assert(env.content.textContent === '', 'Auth loss retained progress');
            assert(env.calls.filter(url => url === '/api/reviewer/progress').length === before, 'Auth loss fetched progress');
            if (page === 'dashboard') {
                const link = env.doc.querySelector('#communityProfileCard a');
                assert(env.card.style.display !== 'none' && link.getAttribute('href') === '/reviewer/profile', 'Profile navigation unavailable');
            } else {
                literal(env.doc.getElementById('stats'), '12');
            }
        }
    });
    await test('progress_stale_requests', async () => {
        for (const page of ['reviewer_profile', 'dashboard']) {
            for (const outcome of ['response', 'json', 'reject']) {
                const env = await progressPage(page, true, progressData(20, 'Private geography'));
                let release;
                const delayed = new Promise((resolve, reject) => { release = outcome === 'reject' ? reject : resolve; });
                env.state.progress = () => outcome === 'json'
                    ? {ok: true, status: 200, json: () => delayed} : delayed;
                env.handlers.pagehide();
                const oldRequest = env.handlers.pageshow({persisted: true});
                for (let i = 0; i < 12; i++) await Promise.resolve();
                env.handlers.pagehide();
                env.state.signedIn = false;
                await env.handlers.pageshow({persisted: true});
                release(outcome === 'response' ? {ok: true, status: 200, json: async () => progressData(20, 'STALE')}
                    : outcome === 'json' ? progressData(20, 'STALE') : new Error('Late failure'));
                await oldRequest;
                assert(env.content.textContent === '', 'Stale request changed cleared content');
            }
        }
    });
    await test('progress_logout', async () => {
        const env = await progressPage('reviewer_profile', true, progressData(20, 'Private geography'));
        env.doc.querySelector('#accountStatus button').click();
        assert(env.content.textContent === '' && env.card.style.display === 'none', 'Logout retained progress');
    });
    await test('recent_activity_content', async () => {
        for (const name of fixtures) {
            const env = await progressPage('reviewer_profile', true, progressData(), 200, 200,
                () => ({ok: true, status: 200, json: async () => activityData(name)}));
            const content = env.doc.getElementById('recentActivityContent');
            assert(!env.doc.getElementById('recentActivitySection').hidden, 'Activity hidden');
            assert(env.calls[0] === '/api/reviewer/profile', 'Activity fetched before profile');
            assert(env.calls.filter(url => url === '/api/reviewer/recent-activity').length === 1, 'Duplicate activity fetch');
            assert(content.querySelectorAll('li').length === 5, 'Not five activity entries');
            assert(!content.querySelector('img, script, b, [onerror]'), 'Stop name became markup');
            const formatter = new Intl.DateTimeFormat(undefined, {year: 'numeric', month: 'short', day: 'numeric',
                hour: 'numeric', minute: '2-digit', timeZoneName: 'short'});
            [...content.querySelectorAll('li')].forEach((row, i) => {
                const link = row.querySelector('a'), time = row.querySelector('time');
                assert(link.textContent === name, 'Stop name changed');
                assert(link.getAttribute('href') === '/stop/' + (9001+i), 'Stop link unusable');
                assert(!row.textContent.includes(String(9001+i)), 'ID visible');
                assert(row.textContent.includes('Review completed'), 'Missing completion label');
                const date = new Date(activityData().activities[i].completed_at);
                assert(time.dateTime === date.toISOString().replace('.000Z', 'Z'), 'Canonical time missing');
                assert(time.textContent === formatter.format(date), 'Time not local');
                const zone = formatter.formatToParts(date).find(part => part.type === 'timeZoneName').value;
                assert(time.textContent.includes(zone), 'Timezone indicator missing');
            });
        }
    });
    await test('recent_activity_states', async () => {
        const signedOut = await progressPage('reviewer_profile', false, progressData());
        assert(!signedOut.calls.includes('/api/reviewer/recent-activity'), 'Signed-out activity fetch');
        assert(signedOut.doc.getElementById('recentActivitySection').hidden, 'Signed-out activity visible');
        for (const status of ['empty', 'unavailable', 'network', 401, 403, 503]) {
            const env = await progressPage('reviewer_profile', true, progressData(), 200, 200, () => {
                if (status === 'network') throw new Error('Offline');
                return {ok: typeof status === 'string', status,
                    json: async () => ({available: status === 'empty', activities: []})};
            });
            const content = env.doc.getElementById('recentActivityContent');
            const expected = status === 'empty' ? 'No completed reviews' :
                [401,403].includes(status) ? 'Sign in again' : 'temporarily unavailable';
            literal(content, expected);
            literal(env.doc.getElementById('stats'), '12');
            assert(env.doc.getElementById('profileName').textContent === 'Existing reviewer', 'Profile disrupted');
            assert(env.doc.querySelector('a[href="/dashboard"]'), 'Navigation lost');
            literal(env.doc.getElementById('stewardedStops'), 'not stewarding');
        }
        let release;
        const pending = new Promise(resolve => { release = resolve; });
        const loading = await progressPage('reviewer_profile', true, progressData(), 200, 200, () => pending);
        literal(loading.doc.getElementById('recentActivityContent'), 'Loading recent activity');
        literal(loading.doc.getElementById('stats'), '12');
        release({ok: true, status: 200, json: async () => activityData()});
    });
    await test('recent_activity_lifecycle', async () => {
        for (const event of ['logout', 'restoration']) {
            for (const outcome of ['response', 'json', 'reject']) {
                const env = await progressPage('reviewer_profile', true, progressData());
                const content = env.doc.getElementById('recentActivityContent');
                assert(content.querySelectorAll('li').length === 5, 'Initial activity missing');
                const calls = env.calls.length;
                await env.handlers.pageshow({persisted: false});
                assert(env.calls.length === calls, 'Initial pageshow duplicated activity');
                let release;
                const delayed = new Promise((resolve, reject) => { release = outcome === 'reject' ? reject : resolve; });
                env.state.activity = () => outcome === 'json'
                    ? {ok: true, status: 200, json: () => delayed} : delayed;
                env.handlers.pagehide();
                const oldRequest = env.handlers.pageshow({persisted: true});
                for (let i = 0; i < 12; i++) await Promise.resolve();
                if (event === 'logout') env.doc.querySelector('#accountStatus button').click();
                else env.handlers.pagehide();
                assert(content.textContent === '', 'Exit retained private activity');
                assert(env.doc.getElementById('recentActivitySection').hidden, 'Exit kept section visible');
                env.state.signedIn = false;
                const before = env.calls.filter(url => url === '/api/reviewer/recent-activity').length;
                await env.handlers.pageshow({persisted: true});
                assert(env.calls.filter(url => url === '/api/reviewer/recent-activity').length === before, 'Auth loss fetched activity');
                release(outcome === 'response' ? {ok: true, status: 200, json: async () => activityData('STALE')}
                    : outcome === 'json' ? activityData('STALE') : new Error('Late failure'));
                await oldRequest;
                assert(content.textContent === '', 'Stale request repopulated private activity');
                literal(env.doc.getElementById('stats'), '12');
                assert(env.doc.querySelector('a[href="/dashboard"]'), 'Navigation lost');
            }
        }
    });
    await test('recent_activity_visibility_auth_loss', async () => {
        for (const authStatus of [200, 401, 403]) {
            for (const outcome of ['response', 'json', 'reject']) {
                const env = await progressPage('reviewer_profile', true, progressData());
                const content = env.doc.getElementById('recentActivityContent');
                assert(content.querySelectorAll('li').length === 5, 'Initial activity missing');
                const hidden = () => {
                    env.state.visibility = 'hidden';
                    env.handlers.visibilitychange();
                    assert(content.textContent === '' && env.doc.getElementById('recentActivitySection').hidden,
                        'Hidden tab retained activity');
                    assert(env.content.textContent === '' && env.card.style.display === 'none',
                        'Hidden tab retained progress');
                };
                hidden();
                let release;
                const pending = new Promise((resolve, reject) => { release = outcome === 'reject' ? reject : resolve; });
                env.state.activity = () => outcome === 'json'
                    ? {ok: true, status: 200, json: () => pending} : pending;
                env.state.visibility = 'visible';
                const staleRequest = env.handlers.visibilitychange();
                for (let i = 0; i < 12; i++) await Promise.resolve();
                hidden();
                env.state.signedIn = false;
                env.state.authStatus = authStatus;
                const before = env.calls.length;
                env.state.visibility = 'visible';
                await env.handlers.visibilitychange();
                assert(JSON.stringify(env.calls.slice(before)) === JSON.stringify(['/api/reviewer/status']),
                    'Tab return did not revalidate or fetched private data after auth loss');
                release(outcome === 'response' ? {ok: true, status: 200, json: async () => activityData('STALE')}
                    : outcome === 'json' ? activityData('STALE') : new Error('Late failure'));
                await staleRequest;
                assert(content.textContent === '' && env.doc.getElementById('recentActivitySection').hidden,
                    'Stale response restored hidden activity');
                literal(env.doc.getElementById('stats'), '12');
                assert(env.doc.getElementById('profileName').textContent === 'Existing reviewer', 'Profile content lost');
                const nav = env.doc.querySelector('a[href="/dashboard"]');
                assert(nav && !nav.closest('[hidden]'), 'Profile navigation hidden');
            }
        }
    });
    await test('recent_activity_visibility_authenticated_once', async () => {
        for (const firstEvent of ['visibility', 'pageshow']) {
            for (const awaitFirst of [false, true]) {
                const env = await progressPage('reviewer_profile', true, progressData());
                for (let cycle = 0; cycle < 2; cycle++) {
                    env.state.visibility = 'hidden';
                    env.handlers.visibilitychange();
                    env.handlers.pagehide();
                    const before = env.calls.length;
                    await env.handlers.pageshow({persisted: true});
                    assert(env.calls.length === before, 'Hidden restoration fetched private data');
                    env.state.visibility = 'visible';
                    const resume = event => event === 'visibility' ? env.handlers.visibilitychange()
                        : env.handlers.pageshow({persisted: true});
                    const first = resume(firstEvent);
                    if (awaitFirst) await first;
                    const second = resume(firstEvent === 'visibility' ? 'pageshow' : 'visibility');
                    await Promise.all([first, second]);
                    assert(JSON.stringify(env.calls.slice(before)) === JSON.stringify([
                        '/api/reviewer/status', '/api/reviewer/progress', '/api/reviewer/recent-activity', '/api/reviewer/achievements'
                    ]), 'Restoration duplicated authentication/progress/activity requests');
                    assert(env.doc.getElementById('recentActivityContent').querySelectorAll('li').length === 5,
                        'Authenticated tab return did not restore activity');
                    assert(!env.doc.getElementById('recentActivitySection').hidden, 'Repopulated activity hidden');
                }
            }
        }
    });
    function awardsResponse() {
        return {ok: true, status: 200, json: async () => ({available: true, achievements: [5, 20].map(count => ({
            family: 'explorer', scope_key: 'global', tier_key: String(count), numerator: count,
            earned_at_utc: '2026-09-29T12:34:56Z'
        }))})};
    }
    await test('achievements_content', async () => {
        const env = await progressPage('reviewer_profile', true, progressData(), 200, 200, null, awardsResponse);
        const card = env.doc.getElementById('privateAchievementsCard');
        const content = env.doc.getElementById('privateAchievementsContent');
        assert(!card.hidden, 'Achievements hidden');
        assert(card.querySelector('details > summary').textContent === 'How recognition works', 'Native disclosure missing');
        assert(!card.querySelector('details').open, 'Disclosure not compact by default');
        literal(card, 'Currently available: Explorer');
        literal(card, 'More recognition categories may be introduced as their rules and data requirements are finalized.');
        literal(card, 'Explorer milestones are 5, 20, 50, and 100 distinct stops.');
        literal(card, 'Qualifying historical reviews can count, including reviews of stops that are no longer active.');
        literal(card, 'Current progress and permanent achievements are separate: progress can change, while an earned award is permanent.');
        for (const count of [5, 20]) {
            literal(content, `Explorer — ${count} stops`);
            literal(content, `Reviewed ${count} distinct qualifying stops`);
        }
        const formatter = new Intl.DateTimeFormat(undefined, {year: 'numeric', month: 'short', day: 'numeric'});
        assert(content.querySelectorAll('time').length === 2, 'Award dates missing');
        for (const time of content.querySelectorAll('time')) {
            assert(time.dateTime === '2026-09-29T12:34:56Z', 'Earned timestamp altered');
            assert(time.textContent === formatter.format(new Date(time.dateTime)), 'Date not reviewer-facing');
        }
        assert(!content.textContent.includes('global'), 'Internal scope exposed');
        assert(env.calls.filter(url => url === '/api/reviewer/achievements').length === 1, 'Duplicate achievements fetch');
        for (const hostile of fixtures) {
            const safe = await progressPage('reviewer_profile', true, progressData(), 200, 200, null, () => ({
                ok: true, status: 200, json: async () => ({available: true, achievements: [{
                    family: 'explorer', tier_key: hostile, numerator: hostile, earned_at_utc: '2026-09-29T12:34:56Z'
                }]})
            }));
            const text = safe.doc.getElementById('privateAchievementsContent');
            literal(text, hostile);
            assert(!text.querySelector('img, script, b, [onerror]'), 'Award values became markup');
        }
    });
    await test('achievements_states', async () => {
        const signedOut = await progressPage('reviewer_profile', false, progressData());
        assert(!signedOut.calls.includes('/api/reviewer/achievements'), 'Signed-out awards fetched');
        assert(signedOut.doc.getElementById('privateAchievementsCard').hidden, 'Signed-out awards visible');
        const empty = await progressPage('reviewer_profile', true, progressData());
        literal(empty.doc.getElementById('privateAchievementsContent'), 'No achievements yet. Complete qualifying reviews at 5 distinct physical stops');
        for (const status of [401, 403, 503, 'network']) {
            const env = await progressPage('reviewer_profile', true, progressData(), 200, 200, null, () => {
                if (status === 'network') throw new Error('Offline');
                return {ok: false, status};
            });
            literal(env.doc.getElementById('privateAchievementsContent'), [401, 403].includes(status) ? 'Sign in again' : 'temporarily unavailable');
            literal(env.doc.getElementById('stats'), '12');
            assert(env.doc.querySelector('a[href="/dashboard"]'), 'Navigation lost');
        }
    });
    await test('achievements_privacy_lifecycle', async () => {
        const env = await progressPage('reviewer_profile', true, progressData(), 200, 200, null, awardsResponse);
        const content = env.doc.getElementById('privateAchievementsContent');
        const card = env.doc.getElementById('privateAchievementsCard');
        literal(content, 'Explorer — 20 stops');
        env.handlers.pagehide();
        assert(card.hidden && content.textContent === '', 'Exit retained awards');
        await env.handlers.pageshow({persisted: true});
        literal(content, 'Explorer — 20 stops');
        let release;
        env.state.achievements = () => new Promise(resolve => { release = resolve; });
        env.handlers.pagehide();
        const pending = env.handlers.pageshow({persisted: true});
        for (let i = 0; i < 12; i++) await Promise.resolve();
        literal(content, 'Loading achievements');
        env.state.visibility = 'hidden';
        env.handlers.visibilitychange();
        env.state.signedIn = false;
        env.state.visibility = 'visible';
        const before = env.calls.length;
        await env.handlers.visibilitychange();
        assert(JSON.stringify(env.calls.slice(before)) === JSON.stringify(['/api/reviewer/status']), 'Auth loss fetched awards');
        release(awardsResponse());
        await pending;
        assert(card.hidden && content.textContent === '', 'Stale awards restored');
        env.state.signedIn = true;
        env.state.achievements = awardsResponse;
        env.handlers.pagehide();
        await env.handlers.pageshow({persisted: true});
        literal(content, 'Explorer — 5 stops');
        env.doc.querySelector('#accountStatus button').click();
        assert(card.hidden && content.textContent === '', 'Logout retained awards');
    });
    // Encode results, not fixture markup, into the only active document.
    document.getElementById('results').textContent = [...new TextEncoder().encode(JSON.stringify(results))]
        .map(byte => byte.toString(16).padStart(2, '0')).join('');
})();

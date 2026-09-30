"""Browser geometry checks for the real jurisdiction table markup and CSS."""
import json
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

from test_html_safety import browser_binary

ROOT = Path(__file__).resolve().parents[1]


class PipelineStickyColumnsTests(unittest.TestCase):
    def test_sticky_columns_and_headers_at_responsive_widths(self):
        binary = browser_binary()
        if not binary:
            self.skipTest('Local Chromium required; set CHROMIUM_BINARY')
        css = (ROOT / 'src/dashboard/static/dashboard.css').read_text(encoding='utf-8')
        template = (ROOT / 'src/dashboard/templates/dashboard.html').read_text(encoding='utf-8')
        table = re.search(r'<table id="pipelineTable">.*?</table>', template, re.S).group()
        fixture = '<!doctype html><style>' + css + '</style><div class="pipeline-table-container">' + table + '</div>'
        script = r'''
(async () => {
    const results = [];
    for (const width of [320, 375, 390, 430, 768, 1280]) {
        const frame = document.createElement('iframe');
        frame.style.cssText = `width:${width}px;height:700px;border:0;display:block`;
        const loaded = new Promise(resolve => frame.onload = resolve);
        frame.srcdoc = FIXTURE;
        document.body.append(frame);
        await loaded;
        const doc = frame.contentDocument, win = frame.contentWindow;
        const table = doc.querySelector('#pipelineTable'), body = table.tBodies[0];
        const scroller = table.parentElement;
        const labels = [
            ['DC Ward', '1'], ['ANC', '8E'], ['State', 'District of Columbia'],
            ['County', "Prince George's County"],
            ['Municipality', 'Friendship Heights Village'],
            ['Municipality', 'AReallyLongUnbrokenGeographyNameForWrapping']
        ];
        body.replaceChildren();
        for (let i = 0; i < 30; i++) {
            const row = body.insertRow();
            for (const value of [...labels[i % labels.length], ...Array(9).fill('123')]) {
                row.insertCell().textContent = value;
            }
        }
        const errors = [];
        const check = (value, message) => { if (!value) errors.push(message); };
        const rect = e => e.getBoundingClientRect();
        const style = e => win.getComputedStyle(e);
        const headers = [...table.tHead.rows[0].cells];
        const typeWidth = rect(headers[0]).width;
        const geographyWidth = rect(headers[1]).width;
        const originalDataLeft = rect(headers[2]).left;
        const maxScroll = scroller.scrollWidth - scroller.clientWidth;
        check(maxScroll > 0, 'No horizontal scrolling');
        check(scroller.clientWidth - typeWidth - geographyWidth >= 40, 'Too little room for scrolling data');
        check(scroller.scrollHeight > scroller.clientHeight, 'No vertical scrolling');
        check(doc.documentElement.scrollWidth <= width, 'Page horizontal overflow');
        check(style(table).display === 'table' && style(table).overflowX === 'visible', 'Nested table scroll owner');
        for (const header of headers) {
            check(style(header).whiteSpace === 'nowrap', 'Compressed header wrapping');
            check(style(header).fontSize === '16px', 'Header font changed');
        }
        for (const [x, y] of [[0, 0], [Math.min(180, maxScroll), 120], [maxScroll, 230]]) {
            scroller.scrollLeft = x; scroller.scrollTop = y;
            const origin = rect(scroller);
            check(Math.abs(rect(headers[0]).left - origin.left) < 1, 'Type header moved');
            check(Math.abs(rect(headers[1]).left - origin.left - typeWidth) < 1, 'Geography offset mismatch');
            check(Math.abs(rect(headers[0]).top - origin.top) < 1, 'Sticky header lost');
            check(Math.abs(rect(headers[2]).top - origin.top) < 1, 'Data header lost top stickiness');
            check(Math.abs(rect(headers[2]).left - (originalDataLeft - x)) < 1, 'Data did not scroll');
            check(rect(headers[1]).right < origin.right, 'Frozen columns hide all data');
            const row = [...body.rows].find(r => rect(r).top > rect(headers[0]).bottom + 2 && rect(r).bottom < origin.bottom);
            check(!!row, 'No visible data row');
            if (!row) continue;
            for (let col = 0; col < 2; col++) {
                const cell = row.cells[col], r = rect(cell), h = rect(headers[col]);
                check(Math.abs(r.left - (origin.left + (col ? typeWidth : 0))) < 1, 'Frozen body cell moved');
                check(style(cell).backgroundColor === 'rgb(255, 255, 255)', 'Transparent sticky body cell');
                check(style(headers[col]).backgroundColor === 'rgb(255, 255, 255)', 'Transparent intersection');
                check(doc.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2) === cell, 'Data paints above frozen body cell');
                check(doc.elementFromPoint(h.left + h.width / 2, h.top + h.height / 2) === headers[col], 'Header intersection layering failed');
                check(Number(style(headers[col]).zIndex) > Number(style(headers[2]).zIndex), 'Intersection z-index too low');
                check(Number(style(headers[2]).zIndex) > Number(style(cell).zIndex), 'Body paints above header');
            }
            check(style(row.cells[1]).boxShadow !== 'none', 'No Geography divider');
            if (x > 0) check([...row.cells].slice(2).some(c => rect(c).left < rect(row.cells[1]).right && rect(c).right > origin.left), 'No data passed behind frozen columns');
        }
        for (const row of body.rows) {
            const cell = row.cells[1];
            check(cell.scrollWidth <= cell.clientWidth, 'Geography text overflows');
            check(style(cell).whiteSpace === 'normal' && style(cell).overflowWrap === 'anywhere', 'Long names cannot wrap');
            check(style(cell).textOverflow !== 'ellipsis', 'Geography name truncated');
        }
        results.push({width, typeWidth, geographyWidth, headerHeight:rect(headers[0]).height,
            horizontalRange:maxScroll, dataWidth:scroller.clientWidth-typeWidth-geographyWidth, pageWidth:doc.documentElement.scrollWidth, errors});
        frame.remove();
    }
    document.querySelector('pre').textContent = [...new TextEncoder().encode(JSON.stringify(results))]
        .map(byte => byte.toString(16).padStart(2, '0')).join('');
})().catch(error => document.querySelector('pre').textContent = String(error.stack || error));
'''.replace('FIXTURE', json.dumps(fixture).replace('<', '\\u003c'))
        page = '<!doctype html><meta charset="utf-8"><pre id="results">pending</pre><script>' + script + '</script>'
        with tempfile.TemporaryDirectory(prefix='dmv-sticky-tests-') as folder:
            path = Path(folder) / 'fixture.html'
            path.write_text(page, encoding='utf-8')
            result = subprocess.run([
                binary, '--headless=new', '--disable-gpu', '--no-first-run',
                '--disable-background-networking', '--disable-extensions', '--dump-dom',
                '--virtual-time-budget=5000', f'--user-data-dir={Path(folder) / "profile"}', path.as_uri(),
            ], capture_output=True, timeout=60,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        output = result.stdout.decode('utf-8', errors='replace')
        match = re.search(r'<pre id="results">([0-9a-f]+)</pre>', output)
        self.assertIsNotNone(match, 'Browser fixture did not complete: ' + output[output.find('<pre'):output.find('</pre>') + 6] + result.stderr.decode('utf-8', errors='replace')[-1000:])
        results = json.loads(bytes.fromhex(match.group(1)).decode('utf-8'))
        self.viewport_results = results
        self.assertEqual([320, 375, 390, 430, 768, 1280], [row['width'] for row in results])
        for row in results:
            with self.subTest(viewport=row['width']):
                self.assertEqual([], row['errors'], row)


if __name__ == '__main__':
    unittest.main()

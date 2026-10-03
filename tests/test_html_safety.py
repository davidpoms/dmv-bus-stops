"""Exercise actual JS renderers in Chromium, using inert detached documents.

No application server/database is used. Hostile-looking fixture values never enter
an active document; CSP also blocks injected script, handlers and network access.
Set CHROMIUM_BINARY to select a local Chrome/Chromium/Edge installation.
"""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def browser_binary():
    candidates = [os.environ.get('CHROMIUM_BINARY')]
    candidates += [shutil.which(name) for name in ('chromium', 'chromium-browser', 'google-chrome', 'msedge')]
    candidates += [r'C:\Program Files\Google\Chrome\Application\chrome.exe',
                   r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe']
    return next((str(path) for path in candidates if path and Path(path).is_file()), None)


class HtmlSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        binary = browser_binary()
        if not binary:
            raise unittest.SkipTest('Local Chromium required; set CHROMIUM_BINARY')
        sources = {name: (ROOT / 'src/dashboard/static' / name).read_text(encoding='utf-8')
                   for name in ('safe_render.js', 'photo_links.js', 'local_evidence.js',
                                'stop_detail.js', 'review_info_loader.js', 'dashboard.js')}
        for name in ('reviewer_profile.html', 'dashboard.html'):
            sources[name] = (ROOT / 'src/dashboard/templates' / name).read_text(encoding='utf-8')
        sources['review.html'] = (ROOT / 'src/dashboard/templates/review.html').read_text(encoding='utf-8')
        cases = (ROOT / 'tests/browser_rendering_cases.js').read_text(encoding='utf-8')
        # Prevent fixture/source strings from terminating the test harness script.
        bundle = json.dumps(sources).replace('<', '\\u003c')
        page = '''<!doctype html><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'nonce-render-tests' 'unsafe-eval'">
<pre id="results">pending</pre><script nonce="render-tests">'''
        page += 'const sources = ' + bundle + ';\n' + cases.replace('</script', '<\\/script') + '</script>'
        with tempfile.TemporaryDirectory(prefix='dmv-render-tests-') as directory:
            folder = Path(directory)
            target = folder / 'test.html'
            target.write_text(page, encoding='utf-8')
            command = [binary, '--headless=new', '--disable-gpu', '--no-first-run',
                       '--no-default-browser-check', '--disable-background-networking',
                       '--disable-extensions', '--lang=en-US', '--dump-dom',
                       '--virtual-time-budget=5000', f'--user-data-dir={folder / "profile"}',
                       target.as_uri()]
            completed = subprocess.run(command, capture_output=True, timeout=60,
                                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            output = completed.stdout.decode('utf-8', errors='replace')
            match = re.search(r'<pre id="results">([0-9a-f]+)</pre>', output)
            if not match:
                raise AssertionError('Browser harness did not finish: ' +
                                     completed.stderr.decode('utf-8', errors='replace')[-2000:] + output[:500])
            cls.results = json.loads(bytes.fromhex(match.group(1)).decode('utf-8'))

    def check_case(self, name):
        self.assertIn(name, self.results)
        self.assertEqual('ok', self.results[name])

    def test_private_progress_authentication_and_failures(self):
        self.check_case('progress_auth')

    def test_achievements_explanation_safe_titles_and_dates(self):
        self.check_case('achievements_content')

    def test_achievements_empty_failure_and_signed_out_states(self):
        self.check_case('achievements_states')

    def test_achievements_private_lifecycle_and_stale_requests(self):
        self.check_case('achievements_privacy_lifecycle')

    def test_private_progress_counts_milestones_and_safe_geography(self):
        self.check_case('progress_content')

    def test_private_progress_restoration_revalidates_authentication(self):
        self.check_case('progress_restoration')

    def test_private_progress_stale_requests_cannot_restore_content(self):
        self.check_case('progress_stale_requests')

    def test_private_progress_logout_clears_content(self):
        self.check_case('progress_logout')

    def test_recent_activity_safe_rows_links_and_local_times(self):
        self.check_case('recent_activity_content')

    def test_recent_activity_loading_empty_failure_and_authentication(self):
        self.check_case('recent_activity_states')

    def test_recent_activity_logout_restoration_and_stale_requests(self):
        self.check_case('recent_activity_lifecycle')

    def test_recent_activity_tab_visibility_auth_loss_and_stale_requests(self):
        self.check_case('recent_activity_visibility_auth_loss')

    def test_recent_activity_authenticated_tab_return_deduplicates_restoration(self):
        self.check_case('recent_activity_visibility_authenticated_once')

    def test_pages_load_safe_renderer_before_consumers(self):
        for name in ('review.html', 'stop_detail.html'):
            source = (ROOT / 'src/dashboard/templates' / name).read_text(encoding='utf-8')
            self.assertLess(source.index('/static/safe_render.js'), source.index('/static/local_evidence.js'))

    def test_dom_text_preserves_literals_and_trusted_markup(self):
        self.check_case('text')

    def test_stop_notes_metadata_names_routes_recommendations(self):
        self.check_case('stop')

    def test_review_notes_metadata_geography_directions_context(self):
        self.check_case('review')

    def test_completion_display_name_routes_and_counts(self):
        self.check_case('completion')

    def test_local_evidence_claims_counts_and_labels(self):
        self.check_case('evidence')

    def test_photo_urls_remain_safe_dom_links(self):
        self.check_case('photos')

    def test_reference_links_reject_unsafe_protocols(self):
        self.check_case('links')

    def test_retired_stop_message_successor_and_url(self):
        self.check_case('retired')

    def test_normal_text_is_unchanged(self):
        self.check_case('normal')

    def test_exposure_formatter_positive_zero_null_missing(self):
        self.check_case('exposure')

    def test_stop_exposure_positive_zero_null_missing(self):
        self.check_case('stop_exposure')

    def test_completion_exposure_positive_zero_null_missing(self):
        self.check_case('completion_exposure')


if __name__ == '__main__':
    unittest.main()

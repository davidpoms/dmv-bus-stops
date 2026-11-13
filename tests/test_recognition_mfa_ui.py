"""Execute the owner page in local headless Chrome with synthetic API responses."""

import html
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

from jinja2 import Environment, FileSystemLoader


ROOT = Path(__file__).resolve().parents[1]
CHROME = shutil.which('google-chrome') or shutil.which('chromium') or shutil.which('chrome')
if not CHROME and os.name == 'nt':
    candidate = Path('C:/Program Files/Google/Chrome/Application/chrome.exe')
    if candidate.is_file():
        CHROME = str(candidate)


@unittest.skipUnless(CHROME, 'Local Chrome/Chromium required; no browser dependency downloaded')
class MfaBrowserTests(unittest.TestCase):
    def test_first_time_setup_existing_enrollment_and_freshness(self):
        fake_api = r"""
<script>
let durable = 'UNENROLLED', requests = [], expired = false, codeRejected = false, fakePendingExpired = false;
const privateUri = 'otpauth://totp/synthetic?secret=SYNTHETICPRIVATEKEY&issuer=Test';
window.fetch = async (url, options = {}) => {
  const path = url.split('/recognition-control/')[1];
  const body = options.body ? JSON.parse(options.body) : null;
  requests.push({path, body});
  let value = {}, ok = true;
  if (path === 'mfa/state') value = {state: durable, pending_expired: fakePendingExpired};
  else if (expired) { ok = false; value = {error: 'recent_primary_authentication_required'}; }
  else if (path === 'mfa/enrollment') {
    durable = 'PENDING'; fakePendingExpired = false; value = {state: 'PENDING_CONFIRMATION', provisioning_uri: privateUri};
  } else if (path === 'mfa/verify') {
    if (codeRejected) {ok = false; value = {error: 'invalid_or_replayed_totp'};}
    else {durable = 'ENROLLED'; value = {state: durable};}
  } else if (path === 'session') value = {state: 'ADMINISTRATIVELY_AUTHENTICATED'};
  else throw Error('Unexpected endpoint');
  return {ok, json: async () => value};
};
console.log = console.warn = console.error = () => { throw Error('Unexpected logging'); };
</script>
"""
        scenario = r"""
<script>
(async () => {
  const check = (value, message) => { if (!value) throw Error(message); };
  const el = id => document.getElementById(id);
  const payload = expected => check(JSON.stringify(requests.at(-1).body) === JSON.stringify(expected), 'payload');
  await refreshMfa();
  check(!el('setup').hidden && el('authenticate').disabled, 'unenrolled controls');
  await el('setup').onclick();
  check(requests.some(r => r.path === 'mfa/enrollment' && JSON.stringify(r.body) === JSON.stringify({csrf_token:'test-csrf'})), 'enrollment payload');
  check(el('provisioning-uri').value === privateUri, 'private URI');
  check(el('setup-key').value === 'SYNTHETICPRIVATEKEY', 'setup key');
  check(!el('output').textContent.includes(privateUri), 'general output leak');
  check(el('setup').hidden && !el('mfa-setup').hidden, 'pending controls');
  el('verification-code').value = '123';
  const before = requests.length;
  await el('verify-form').onsubmit({preventDefault(){}});
  check(requests.length === before, 'invalid length submitted');
  codeRejected = true;
  el('verification-code').value = '000000';
  await el('verify-form').onsubmit({preventDefault(){}});
  payload({code:'000000',csrf_token:'test-csrf'});
  check(durable === 'PENDING' && el('output').textContent.includes('invalid_or_replayed_totp'), 'invalid code');
  codeRejected = false;
  el('verification-code').value = '123456';
  await el('verify-form').onsubmit({preventDefault(){}});
  check(requests.at(-2).path === 'mfa/verify' && requests.at(-1).path === 'mfa/state', 'durable refresh');
  check(durable === 'ENROLLED' && !el('authenticate').disabled && el('setup').hidden, 'enrolled controls');
  check(!el('provisioning-uri').value && !el('setup-key').value && !el('verification-code').value, 'secret clearing');
  check(el('output').textContent.includes('NEW authenticator code'), 'new code instruction');
  window.prompt = () => '654321';
  await el('authenticate').onclick();
  check(requests.at(-1).path === 'session', 'existing session endpoint');
  payload({code:'654321',csrf_token:'test-csrf'});
  durable = 'UNENROLLED'; await refreshMfa();
  expired = true; await el('setup').onclick();
  check(el('output').textContent.includes('Sign out and sign in again'), 'freshness guidance');
  expired = false; await el('setup').onclick();
  window.dispatchEvent(new Event('pagehide'));
  check(!el('provisioning-uri').value && !el('setup-key').value, 'pagehide secrets');
  fakePendingExpired = true;
  await el('refresh-mfa').onclick();
  check(durable === 'PENDING' && !el('setup').hidden, 'expired pending eligibility');
  check(el('setup').textContent === 'Restart MFA setup', 'restart label');
  check(el('mfa-help').textContent.includes('Sign in afresh'), 'restart freshness guidance');
  await el('setup').onclick();
  check(durable === 'PENDING' && !fakePendingExpired && el('setup').hidden, 'new pending');
  check(el('provisioning-uri').value === privateUri, 'visible restart provisioning');
  check(requests.every(r => ['mfa/state','mfa/enrollment','mfa/verify','session'].includes(r.path)), 'activation called');
  check(localStorage.length === 0 && sessionStorage.length === 0, 'browser storage');
  el('browser-result').textContent = 'PASS';
})().catch(error => { document.getElementById('browser-result').textContent = 'FAIL: ' + error.message; });
</script>
"""
        self.run_browser(fake_api,scenario)

    def test_hidden_inflight_response_cannot_restore_provisioning(self):
        fake_api = r"""
<script>
let durable = 'UNENROLLED', resolveEnrollment, hiddenForTest = false;
Object.defineProperty(document, 'hidden', {get: () => hiddenForTest});
window.fetch = async (url) => {
  if (url.endsWith('mfa/state')) return {ok:true,json:async()=>({state:durable,pending_expired:false})};
  if (!url.endsWith('mfa/enrollment')) throw Error('Unexpected endpoint');
  return new Promise(resolve => {resolveEnrollment = () => {
    durable = 'PENDING';
    resolve({ok:true,json:async()=>({state:'PENDING_CONFIRMATION',
      provisioning_uri:'otpauth://totp/synthetic?secret=SYNTHETICPRIVATEKEY'})});
  };});
};
console.log = console.warn = console.error = () => {throw Error('Unexpected logging');};
</script>
"""
        scenario = r"""
<script>
(async () => {
  const el = id => document.getElementById(id);
  const check = (value) => {if (!value) throw Error('Secret lifecycle failure');};
  const cleared = () => !el('provisioning-uri').value && !el('setup-key').value && !el('verification-code').value;
  for (const returnBeforeResponse of [false,true]) {
    hiddenForTest = false; durable = 'UNENROLLED'; await refreshMfa();
    const enrollment = el('setup').onclick();
    check(typeof resolveEnrollment === 'function');
    hiddenForTest = true;
    document.dispatchEvent(new Event('visibilitychange'));
    check(cleared());
    if (returnBeforeResponse) {
      hiddenForTest = false;
      document.dispatchEvent(new Event('visibilitychange'));
    }
    resolveEnrollment();
    await enrollment;
    check(cleared());
    check(!el('output').textContent.includes('SYNTHETICPRIVATEKEY'));
    hiddenForTest = false;
    document.dispatchEvent(new Event('visibilitychange'));
    check(cleared());
  }
  el('browser-result').textContent = 'PASS';
})().catch(() => {document.getElementById('browser-result').textContent = 'FAIL';});
</script>
"""
        self.run_browser(fake_api,scenario)

    def run_browser(self,fake_api,scenario):
        template = Environment(loader=FileSystemLoader(ROOT/'src/dashboard/templates')).get_template(
            'recognition_runtime_activation.html').render(csrf_token='test-csrf')
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'page.html'
            page = template.replace('<script>', fake_api+'<script>', 1)
            path.write_text(page+'<pre id="browser-result"></pre>'+scenario, encoding='utf-8')
            result = subprocess.run([CHROME, '--headless=new', '--disable-gpu', '--no-first-run',
                '--no-default-browser-check', '--allow-file-access-from-files',
                '--user-data-dir='+str(Path(folder)/'profile'), '--dump-dom',
                '--virtual-time-budget=5000', path.as_uri()],
                capture_output=True, text=True, timeout=45,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            self.assertEqual(0, result.returncode, 'Headless browser failed')
            match = re.search(r'<pre id="browser-result">(.*?)</pre>', result.stdout)
            self.assertIsNotNone(match, 'Browser result missing')
            self.assertEqual('PASS', html.unescape(match.group(1)))


if __name__ == '__main__':
    unittest.main()

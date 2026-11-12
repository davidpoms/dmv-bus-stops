"""Fresh CLI bootstrap ordering and fail-closed tests, with database access forbidden."""

from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/active/manage_recognition_administration.py'


class AdministrativeCliStartupTests(unittest.TestCase):
    def run_child(self, body):
        code = '''
import os, runpy, sys
from src.api import sqlite_runtime as runtime
assert 'sqlite3' not in sys.modules and '_sqlite3' not in sys.modules
assert not any(n.startswith('src.review.recognition') for n in sys.modules)
def guard(event, args):
    if event == 'sqlite3.connect':
        raise AssertionError('CLI bootstrap test forbids every database connection')
sys.addaudithook(guard)
script = sys.argv[1]
sys.argv = [script, '--help']
''' + body
        result = subprocess.run([sys.executable, '-B', '-c', code, str(SCRIPT)],
                                cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(0, result.returncode, result.stderr)
        return result

    def test_preload_precedes_every_recognition_import_and_preserves_help(self):
        result = self.run_child('''
events = []
class RecognitionImportGuard:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith('src.review.recognition'):
            assert events and events[0] == 'preloaded', fullname
            events.append(fullname)
        return None
sys.meta_path.insert(0, RecognitionImportGuard())
def preload():
    assert 'sqlite3' not in sys.modules and '_sqlite3' not in sys.modules
    assert not any(n.startswith('src.review.recognition') for n in sys.modules)
    events.append('preloaded')
runtime.load_production_sqlite = preload
try:
    runpy.run_path(script, run_name='__main__')
except SystemExit as error:
    assert error.code == 0
else:
    raise AssertionError('argparse help was not reached')
assert events.count('preloaded') == 1
assert 'src.review.recognition.administration' in events
''')
        self.assertIn('migrate-runtime-profile-contract', result.stdout)
        self.assertIn('--expected-generation', result.stdout)

    def test_missing_configuration_stops_before_administration_import(self):
        self.run_child('''
os.environ.pop(runtime.ENVIRONMENT, None)
# Portable isolation of the real configuration guard from the Linux ELF guard.
runtime._fresh = lambda: None
try:
    runpy.run_path(script, run_name='__main__')
except RuntimeError as error:
    assert str(error) == 'sqlite_runtime_explicit_library_required', str(error)
else:
    raise AssertionError('CLI accepted absent private-runtime configuration')
assert not any(n.startswith('src.review.recognition') for n in sys.modules)
assert 'sqlite3' not in sys.modules and '_sqlite3' not in sys.modules
''')

    def test_load_failure_propagates_without_administration_import(self):
        self.run_child('''
def fail():
    raise OSError('synthetic native load failure')
runtime.load_production_sqlite = fail
try:
    runpy.run_path(script, run_name='__main__')
except OSError as error:
    assert str(error) == 'synthetic native load failure'
else:
    raise AssertionError('CLI continued after preload failure')
assert not any(n.startswith('src.review.recognition') for n in sys.modules)
assert 'sqlite3' not in sys.modules and '_sqlite3' not in sys.modules
''')

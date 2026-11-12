"""Private-loader guards and disposable native integration; no production paths."""

import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from src.api import sqlite_runtime as runtime
from scripts.active import build_private_sqlite as builder
from tests.recognition_production_owner_fixture import allocation


ROOT = Path(__file__).resolve().parents[1]


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(allocation())
        self.root = Path(self.enterContext(tempfile.TemporaryDirectory())).resolve()
        self.enterContext(patch.object(runtime, 'approved_directory', return_value=self.root / runtime.VERSION))
        self.enterContext(patch.object(runtime, '_handle', None))
        self.enterContext(patch.object(runtime, '_failed', False))

    def test_module_import_does_not_import_sqlite(self):
        result = subprocess.run([sys.executable, '-B', '-c',
            'import sys; from src.api import sqlite_runtime; '
            'assert "sqlite3" not in sys.modules and "_sqlite3" not in sys.modules'],
            cwd=ROOT, capture_output=True, text=True, timeout=20)
        self.assertEqual(0, result.returncode, result.stderr)

    def test_already_imported_refused_before_load(self):
        with patch.object(runtime.sys, 'platform', 'linux'), patch.object(runtime.platform, 'machine', return_value='x86_64'), \
                patch.object(runtime.ctypes, 'CDLL') as load:
            with self.assertRaisesRegex(RuntimeError, 'sqlite_already_imported'):
                runtime.load_production_sqlite()
        load.assert_not_called()

    def test_already_mapped_refused_before_load(self):
        with patch.object(runtime.sys, 'platform', 'linux'), patch.object(runtime.platform, 'machine', return_value='x86_64'), \
                patch.object(runtime.sys, 'modules', {}), patch.object(runtime, '_mappings', return_value=['/system/libsqlite3.so.0']), \
                patch.object(runtime.ctypes, 'CDLL') as load:
            with self.assertRaisesRegex(RuntimeError, 'sqlite_already_mapped'):
                runtime._fresh()
        load.assert_not_called()

    def test_missing_relative_and_outside_paths(self):
        for raw, code in ((None, 'explicit_library_required'), ('relative.so', 'outside_approved_directory'),
                          (str(self.root / 'outside.so'), 'outside_approved_directory')):
            with self.subTest(raw=raw), patch.dict(os.environ, {}, clear=True):
                if raw is not None:
                    os.environ[runtime.ENVIRONMENT] = raw
                with self.assertRaisesRegex(RuntimeError, code):
                    runtime._configured_library()
        with patch.dict(os.environ, {runtime.ENVIRONMENT: str(runtime.approved_directory() / 'lib' / runtime.SONAME)}):
            with self.assertRaises(FileNotFoundError):
                runtime._configured_library()

    def test_manifest_hash_and_architecture_are_checked(self):
        version = self.root / runtime.VERSION
        (version / 'lib').mkdir(parents=True)
        library = version / 'lib' / runtime.SONAME
        header = b'\x7fELF\x02\x01' + b'\0' * 12 + b'\x3e\0'
        library.write_bytes(header)
        manifest = dict(format='recognition-private-sqlite-v1', sqlite_version=runtime.VERSION,
            archive_sha3_256=runtime.ARCHIVE_SHA3, soname=runtime.SONAME,
            architecture='ELF64 x86-64', compile_flags=list(runtime.FLAGS),
            library_sha256=hashlib.sha256(header).hexdigest())
        path = version / 'manifest.json'
        path.write_text(json.dumps(manifest))
        with patch.object(runtime, 'approved_directory', return_value=version), \
                patch.object(runtime, '_private'), patch.dict(os.environ, {runtime.ENVIRONMENT: str(library)}):
            self.assertEqual((library, manifest['library_sha256']), runtime._configured_library())
            library.write_bytes(header + b'changed')
            with self.assertRaisesRegex(RuntimeError, 'library_hash_mismatch'):
                runtime._configured_library()
            manifest['library_sha256'] = hashlib.sha256(b'not ELF').hexdigest()
            path.write_text(json.dumps(manifest))
            library.write_bytes(b'not ELF')
            with self.assertRaisesRegex(RuntimeError, 'wrong_elf_architecture'):
                runtime._configured_library()

    def test_unsafe_permissions_symlinks_and_hardlinks_rejected(self):
        import stat
        path = unittest.mock.Mock()
        for mode, uid, links, code in (
                (stat.S_IFLNK | 0o700, 100, 1, 'symlink_forbidden'),
                (stat.S_IFREG | 0o666, 100, 1, 'unsafe_owner_or_permissions'),
                (stat.S_IFREG | 0o600, 101, 1, 'unsafe_owner_or_permissions'),
                (stat.S_IFREG | 0o600, 100, 2, 'hardlink_forbidden')):
            with self.subTest(code=code), patch.object(runtime.os, 'geteuid', return_value=100, create=True):
                path.lstat.return_value = SimpleNamespace(st_mode=mode, st_uid=uid, st_nlink=links)
                with self.assertRaisesRegex(RuntimeError, code):
                    runtime._private(path)

    def test_loader_environment_override_rejected(self):
        for name in ('LD_LIBRARY_PATH', 'LD_PRELOAD'):
            with self.subTest(name=name), patch.object(runtime.sys, 'platform', 'linux'), \
                    patch.object(runtime.platform, 'machine', return_value='x86_64'), \
                    patch.object(runtime.sys, 'modules', {}), patch.object(runtime, '_mappings', return_value=[]), \
                    patch.dict(os.environ, {name: '/unapproved'}):
                with self.assertRaisesRegex(RuntimeError, 'loader_environment_override_forbidden'):
                    runtime._fresh()

    def test_wrong_version_rejected(self):
        with patch.object(sqlite3, 'sqlite_version', '3.37.2'):
            with self.assertRaisesRegex(RuntimeError, 'wrong_sqlite_version'):
                runtime._verify(self.root / 'library.so')

    def test_missing_operator_rejected(self):
        from src.review.recognition import sqlite_capabilities
        with patch.object(runtime, 'VERSION', sqlite3.sqlite_version), \
                patch.object(sqlite_capabilities, 'inspect_connection', return_value={'supported': False}):
            with self.assertRaisesRegex(RuntimeError, 'json_operators_required'):
                runtime._verify(self.root / 'library.so')

    def test_four_large_inodes_and_memory_only_verification(self):
        library = self.root / 'library.so'
        before = list(self.root.iterdir())
        original = sqlite3.connect
        with patch.object(runtime, 'VERSION', sqlite3.sqlite_version), \
                patch.object(runtime, '_mappings', return_value=[str(library)]), \
                patch.object(sqlite3, 'connect', wraps=original) as connect:
            report = runtime._verify(library)
        self.assertTrue(report['exact_inode_text'])
        connect.assert_called_once_with(':memory:')
        self.assertEqual(before, list(self.root.iterdir()))

    def test_precision_failure_rejected(self):
        class RoundedConnection:
            def execute(self, *args):
                return self
            def fetchone(self):
                return ('18446744073709552000', 'text', 0)
            def close(self):
                pass
        from src.review.recognition import sqlite_capabilities
        with patch.object(runtime, 'VERSION', sqlite3.sqlite_version), \
                patch.object(sqlite3, 'connect', return_value=RoundedConnection()), \
                patch.object(sqlite_capabilities, 'inspect_connection', return_value={'supported': True}):
            with self.assertRaisesRegex(RuntimeError, 'inode_precision_failure'):
                runtime._verify(self.root / 'library.so')

    def test_load_failure_poisoned_and_no_fallback(self):
        with patch.object(runtime, '_fresh'), patch.object(runtime.os, 'RTLD_NOW', 2, create=True), \
                patch.object(runtime.os, 'RTLD_GLOBAL', 256, create=True), \
                patch.object(runtime.ctypes, 'CDLL', side_effect=OSError('synthetic load failure')):
            with self.assertRaises(OSError):
                runtime._load_candidate(self.root / 'library.so')
        self.assertTrue(runtime._failed)
        with self.assertRaisesRegex(RuntimeError, 'verified_preload_required'):
            runtime.inspect_loaded_sqlite()

    def test_fresh_subprocess_orchestration_and_app_import(self):
        # Portable orchestration test, NOT a substitute for the Linux native test.
        code = r'''
import sys, os
from pathlib import Path
from unittest.mock import patch
from src.api import sqlite_runtime as r
assert 'sqlite3' not in sys.modules
library=Path(sys.argv[1])/'library.so'
os.environ['PYTHON_DOTENV_DISABLED']='1'
os.environ['LIVE_RECOGNITION_CAPTURE']='0'
os.environ['DMV_BUS_STOPS_DB']=str(Path(sys.argv[1])/'never-created.db')
os.environ['RECOGNITION_ADMIN_CONTROL']=''
os.environ['RECOGNITION_ADMIN_KEY_FILE']=''
with patch.object(r,'_fresh'), patch.object(r,'_configured_library',return_value=(library,'synthetic')), \
     patch.object(r.ctypes,'CDLL',return_value=object()) as cdll, \
     patch.object(r.os,'RTLD_NOW',2,create=True),patch.object(r.os,'RTLD_GLOBAL',256,create=True):
    import sqlite3
    with patch.object(r,'VERSION',sqlite3.sqlite_version),patch.object(r,'_mappings',return_value=[str(library)]):
        def memory_only(event,args):
            if event=='sqlite3.connect' and args[0]!=':memory:': raise AssertionError('file database forbidden')
        sys.addaudithook(memory_only)
        assert r.load_production_sqlite()['supported']
        cdll.assert_called_once_with(str(library),mode=2|r.os.RTLD_GLOBAL)
        from src.api.app import app
        import _sqlite3
        assert sqlite3.Connection is _sqlite3.Connection
        assert r.inspect_loaded_sqlite()['supported']
        assert not app.config['LIVE_RECOGNITION_GATE'].capture
assert not (Path(sys.argv[1])/'never-created.db').exists()
'''
        before = sqlite3.sqlite_version
        result = subprocess.run([sys.executable, '-B', '-c', code, str(self.root)],
                                cwd=ROOT, text=True, capture_output=True, timeout=45)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(before, sqlite3.sqlite_version)

    def test_builder_refuses_existing_version(self):
        with patch.object(builder.sys, 'platform', 'linux'), \
                patch.object(builder.platform, 'machine', return_value='x86_64'), \
                patch.object(runtime, 'approved_directory', return_value=self.root), \
                patch.dict(os.environ, {}, clear=True), patch.object(builder, '_download') as download:
            with self.assertRaisesRegex(RuntimeError, 'runtime_destination_exists'):
                builder.build()
        download.assert_not_called()

    def test_archive_checksum_mismatch_stops_before_build(self):
        row = 'PRODUCT,3.54.1,2026/' + runtime.ARCHIVE + ',1,' + runtime.ARCHIVE_SHA3
        responses = [io.BytesIO(row.encode()), io.BytesIO(b'wrong archive')]
        with patch.object(builder.urllib.request, 'urlopen', side_effect=responses):
            with self.assertRaisesRegex(RuntimeError, 'archive_checksum_mismatch'):
                builder._download()

    def test_unexpected_second_library_fails_closed(self):
        with patch.object(runtime, 'VERSION', sqlite3.sqlite_version), \
                patch.object(runtime, '_mappings', return_value=['/system/libsqlite3.so.0']):
            with self.assertRaisesRegex(RuntimeError, 'unexpected_mapped_sqlite'):
                runtime._verify(self.root / 'library.so')

    def test_builder_publishes_manifest_only_after_candidate_validation(self):
        import zipfile
        source = io.BytesIO()
        with zipfile.ZipFile(source, 'w') as archive:
            for name in ('sqlite3.c', 'sqlite3.h'):
                archive.writestr(runtime.ARCHIVE[:-4] + '/' + name, 'synthetic source')
        destination = self.root / runtime.VERSION
        command_seen = []
        mkdir = Path.mkdir
        def portable_mkdir(path, mode=0o777, parents=False, exist_ok=False):
            return mkdir(path, mode=0o777, parents=parents, exist_ok=exist_ok)
        def run(command, **kwargs):
            command_seen.append(command)
            if '-o' in command:
                Path(command[command.index('-o') + 1]).write_bytes(
                    b'\x7fELF\x02\x01' + b'\0' * 12 + b'\x3e\0')
                return subprocess.CompletedProcess(command, 0)
            return subprocess.CompletedProcess(command, 0, stdout='(SONAME) [' + runtime.SONAME + ']')
        with patch.object(builder.sys, 'platform', 'linux'), \
                patch.object(builder.platform, 'machine', return_value='x86_64'), \
                patch.dict(os.environ, {}, clear=True), patch.object(runtime, '_private'), \
                patch.object(builder.shutil, 'which', side_effect=lambda name: '/usr/bin/' + name), \
                patch.object(builder, '_download', return_value=('https://www.sqlite.org/example.zip', source.getvalue())), \
                patch.object(builder.subprocess, 'run', side_effect=run), \
                patch.object(Path, 'mkdir', portable_mkdir), patch.object(Path, 'chmod'), \
                patch.object(builder, '_candidate_probe', side_effect=[RuntimeError('synthetic verification failure'),
                    {'supported': True, 'sqlite_runtime_version': runtime.VERSION}]):
            with self.assertRaisesRegex(RuntimeError, 'synthetic verification failure'):
                builder.build()
            self.assertFalse(destination.exists())
            manifest = builder.build()
        self.assertEqual(list(runtime.FLAGS), manifest['compile_flags'])
        self.assertEqual(runtime.ARCHIVE_SHA3, manifest['archive_sha3_256'])
        self.assertEqual(runtime.SONAME, manifest['soname'])
        self.assertEqual(hashlib.sha256((destination / 'lib' / runtime.SONAME).read_bytes()).hexdigest(),
                         manifest['library_sha256'])
        self.assertEqual(manifest, json.loads((destination / 'manifest.json').read_text()))
        self.assertEqual(4, len(command_seen))


@unittest.skipUnless(sys.platform == 'linux' and os.environ.get('RUN_PRIVATE_SQLITE_NATIVE') == '1',
                     'requires opt-in disposable Linux x86-64 gcc build and official download')
class NativeIntegrationTests(unittest.TestCase):
    def test_build_preload_app_import_and_unchanged_normal_runtime(self):
        with tempfile.TemporaryDirectory() as raw:
            # Both processes share a disposable HOME, never the production home.
            env = dict(os.environ, HOME=raw, PYTHON_DOTENV_DISABLED='1', LIVE_RECOGNITION_CAPTURE='0',
                       DMV_BUS_STOPS_DB=str(Path(raw) / 'never-created.db'),
                       RECOGNITION_ADMIN_CONTROL='', RECOGNITION_ADMIN_KEY_FILE='')
            env.pop('LD_LIBRARY_PATH', None)
            env.pop('LD_PRELOAD', None)
            baseline = subprocess.check_output([sys.executable, '-B', '-c',
                'import sqlite3; print(sqlite3.sqlite_version)'], env=env, text=True, timeout=20)
            subprocess.run([sys.executable, '-B', 'scripts/active/build_private_sqlite.py'],
                           cwd=ROOT, env=env, check=True, timeout=780)
            library = Path(raw) / 'sqlite-runtime' / runtime.VERSION / 'lib' / runtime.SONAME
            env[runtime.ENVIRONMENT] = str(library)
            code = '''
import sys
def guard(event,args):
    if event=='sqlite3.connect' and args[0]!=':memory:': raise AssertionError('file database forbidden')
sys.addaudithook(guard)
from src.api.sqlite_runtime import load_production_sqlite, inspect_loaded_sqlite
assert load_production_sqlite()['supported']
from src.api.app import app
assert inspect_loaded_sqlite()['supported']
'''
            subprocess.run([sys.executable, '-B', '-c', code], env=env, cwd=ROOT, check=True, timeout=45)
            after = subprocess.check_output([sys.executable, '-B', '-c',
                'import sqlite3; print(sqlite3.sqlite_version)'], env=env, text=True, timeout=20)
            self.assertEqual(baseline, after)
            self.assertFalse((Path(raw) / 'never-created.db').exists())

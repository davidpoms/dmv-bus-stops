"""Opt-in Linux startup loader. Import this BEFORE any sqlite3/application import.

Only trusted owner-built native code is loaded. This is runtime selection, not
authentication, activation, database access or execution authorization.
"""

import ctypes
import hashlib
import json
import os
from pathlib import Path
import platform
import stat
import sys


VERSION = '3.54.1'
ARCHIVE = 'sqlite-amalgamation-3540100.zip'
ARCHIVE_SHA3 = '92281c86e2957f9b9305890f9ac04204caa7b677cc868dc326d942689df28e30'
SONAME = 'libsqlite3.so.0'
FLAGS = ('-O2', '-fPIC', '-shared', '-DSQLITE_THREADSAFE=1',
         '-DSQLITE_ENABLE_COLUMN_METADATA', '-Wl,-soname,' + SONAME)
ENVIRONMENT = 'RECOGNITION_SQLITE_LIBRARY'
_handle = None
_failed = False


def _need(value, code):
    if not value:
        raise RuntimeError('sqlite_runtime_' + code)


def approved_directory():
    return Path.home() / 'sqlite-runtime' / VERSION


def _mappings():
    """Actual process mappings, not the predictions of a separate ldd process."""
    paths = set()
    for line in Path('/proc/self/maps').read_text(encoding='utf-8').splitlines():
        if 'libsqlite3' in line:
            fields = line.split(None, 5)
            _need(len(fields) == 6 and not fields[5].endswith(' (deleted)'), 'invalid_mapping')
            paths.add(str(Path(fields[5]).resolve(strict=True)))
    return sorted(paths)


def _fresh():
    _need(sys.platform == 'linux' and platform.machine() == 'x86_64', 'linux_x86_64_required')
    _need(not _failed and _handle is None, 'preload_already_attempted')
    _need('sqlite3' not in sys.modules and '_sqlite3' not in sys.modules, 'sqlite_already_imported')
    _need(not _mappings(), 'sqlite_already_mapped')
    _need(not os.environ.get('LD_LIBRARY_PATH') and not os.environ.get('LD_PRELOAD'),
          'loader_environment_override_forbidden')


def _private(path, *, directory=False):
    info = path.lstat()
    _need(not stat.S_ISLNK(info.st_mode), 'symlink_forbidden')
    _need(stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode), 'invalid_file_type')
    _need(info.st_uid == os.geteuid() and not info.st_mode & 0o022, 'unsafe_owner_or_permissions')
    if not directory:
        _need(info.st_nlink == 1, 'hardlink_forbidden')


def _configured_library():
    raw = os.environ.get(ENVIRONMENT)
    _need(bool(raw), 'explicit_library_required')
    library = Path(raw)
    expected = approved_directory() / 'lib' / SONAME
    _need(library.is_absolute() and library == expected, 'library_outside_approved_directory')
    _need(library.resolve(strict=True) == library, 'noncanonical_library_path')
    for directory in (approved_directory().parent, approved_directory(), library.parent):
        _private(directory, directory=True)
    _private(library)
    manifest_path = approved_directory() / 'manifest.json'
    _private(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    _need(manifest.get('format') == 'recognition-private-sqlite-v1'
          and manifest.get('sqlite_version') == VERSION
          and manifest.get('archive_sha3_256') == ARCHIVE_SHA3
          and manifest.get('soname') == SONAME
          and manifest.get('architecture') == 'ELF64 x86-64'
          and manifest.get('compile_flags') == list(FLAGS), 'manifest_contract_mismatch')
    actual = hashlib.sha256(library.read_bytes()).hexdigest()
    _need(manifest.get('library_sha256') == actual, 'library_hash_mismatch')
    header = library.read_bytes()[:20]
    _need(header[:6] == b'\x7fELF\x02\x01' and header[18:20] == b'\x3e\x00', 'wrong_elf_architecture')
    return library, actual


def _verify(library):
    # Deliberately delayed: native library must be loaded first.
    import sqlite3
    import _sqlite3
    from src.review.recognition.sqlite_capabilities import inspect_connection

    _need(sqlite3.Connection is _sqlite3.Connection, 'standard_library_driver_required')
    _need(sqlite3.sqlite_version == VERSION, 'wrong_sqlite_version')
    _need(sqlite3.threadsafety > 0, 'threadsafe_sqlite_required')
    conn = sqlite3.connect(':memory:')
    try:
        capabilities = inspect_connection(conn)
        _need(capabilities['supported'], 'json_operators_required')
        for inode in ('9223372036854775807', '9223372036854775808',
                      '18446744073709551614', '18446744073709551615'):
            document = '{"inode":' + inode + '}'
            raw, kind, equal = conn.execute(
                "SELECT ? -> '$.inode', typeof(? -> '$.inode'), ? = (? -> '$.inode')",
                (document, document, inode, document)).fetchone()
            _need(type(raw) is str and raw == inode and kind == 'text' and equal == 1,
                  'inode_precision_failure')
    finally:
        conn.close()
    mappings = _mappings()
    _need(mappings == [str(library)], 'unexpected_mapped_sqlite')
    return dict(python_version=platform.python_version(), pid=os.getpid(),
        sqlite_extension=_sqlite3.__file__, sqlite_runtime_version=sqlite3.sqlite_version,
        expected_library=str(library), mapped_libraries=mappings,
        operators=capabilities['operators'], exact_inode_text=True, supported=True)


def _load_candidate(library):
    """Builder-only fresh-process validation; does not authorize installation."""
    global _handle, _failed
    try:
        _fresh()
        _handle = ctypes.CDLL(str(library), mode=os.RTLD_NOW | os.RTLD_GLOBAL)
        return _verify(library)
    except BaseException:
        _failed = True
        raise


def _failure_report(error):
    try:
        mappings = _mappings()
    except (OSError, RuntimeError):
        mappings = None
    code = str(error) if type(error) is RuntimeError and str(error).startswith('sqlite_runtime_') else type(error).__name__
    sqlite = sys.modules.get('sqlite3')
    extension = sys.modules.get('_sqlite3')
    return dict(python_version=platform.python_version(), pid=os.getpid(),
        sqlite_extension=getattr(extension, '__file__', None),
        sqlite_runtime_version=getattr(sqlite, 'sqlite_version', None),
        expected_library=str(approved_directory() / 'lib' / SONAME),
        mapped_libraries=mappings, operators=None, exact_inode_text=None,
        supported=False, error=code)


def load_production_sqlite():
    """Fail closed; retain the handle. Never fall back or retry in this process."""
    global _failed
    try:
        # Validate freshness before reading any configured native artifact.
        _fresh()
        library, sha256 = _configured_library()
        report = _load_candidate(library)
        # Detect observed replacement during loading; trusted owner is the boundary.
        _need(_configured_library() == (library, sha256), 'artifact_changed_during_load')
        report['library_sha256'] = sha256
        sys.stderr.write('recognition_sqlite_startup ' + json.dumps(report, sort_keys=True) + '\n')
        return report
    except BaseException as error:
        _failed = True
        sys.stderr.write('recognition_sqlite_startup ' + json.dumps(_failure_report(error), sort_keys=True) + '\n')
        raise


def inspect_loaded_sqlite():
    """Recheck this process, without preloading or opening database files."""
    _need(_handle is not None and not _failed, 'verified_preload_required')
    library, sha256 = _configured_library()
    report = _verify(library)
    report['library_sha256'] = sha256
    return report

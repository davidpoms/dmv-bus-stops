"""Build pinned owner-local SQLite. Never changes WSGI, databases or virtualenvs."""

import csv
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.api import sqlite_runtime as runtime


def _download():
    page = urllib.request.urlopen('https://www.sqlite.org/download.html', timeout=60).read().decode('utf-8')
    rows = [next(csv.reader(io.StringIO(line))) for line in page.splitlines() if line.startswith('PRODUCT,')]
    matches = [r for r in rows if len(r) >= 5 and r[2].endswith('/' + runtime.ARCHIVE)]
    runtime._need(len(matches) == 1, 'pinned_official_archive_unavailable')
    relative = matches[0][2]
    runtime._need(not relative.startswith(('/', '.')) and '://' not in relative
                  and matches[0][4].strip().lower() == runtime.ARCHIVE_SHA3, 'archive_metadata_mismatch')
    url = 'https://www.sqlite.org/' + relative
    archive = urllib.request.urlopen(url, timeout=60).read()
    runtime._need(hashlib.sha3_256(archive).hexdigest() == runtime.ARCHIVE_SHA3, 'archive_checksum_mismatch')
    return url, archive


def _candidate_probe(library):
    code = ('import json,sys; sys.path.insert(0,sys.argv[1]); '
            'from src.api.sqlite_runtime import _load_candidate; '
            'from pathlib import Path; print(json.dumps(_load_candidate(Path(sys.argv[2]))))')
    result = subprocess.run([sys.executable, '-B', '-c', code, str(ROOT), str(library)],
        check=True, capture_output=True, text=True, timeout=60)
    return json.loads(result.stdout)


def build():
    runtime._need(sys.platform == 'linux' and platform.machine() == 'x86_64', 'linux_x86_64_required')
    runtime._need(not os.environ.get('LD_LIBRARY_PATH') and not os.environ.get('LD_PRELOAD'),
                  'loader_environment_override_forbidden')
    destination = runtime.approved_directory()
    parent = destination.parent
    runtime._need(not destination.exists() and not destination.is_symlink(), 'runtime_destination_exists')
    parent.mkdir(mode=0o700, exist_ok=True)
    runtime._need(parent.resolve() == parent, 'noncanonical_runtime_directory')
    runtime._private(parent, directory=True)
    compiler = shutil.which('gcc')
    readelf = shutil.which('readelf')
    runtime._need(compiler and readelf, 'gcc_and_readelf_required')
    url, archive = _download()
    # Staging is separate from the published version; never overwrite a runtime.
    with tempfile.TemporaryDirectory(prefix='.sqlite-build-', dir=parent) as raw:
        work = Path(raw)
        with zipfile.ZipFile(io.BytesIO(archive)) as source:
            for name in ('sqlite3.c', 'sqlite3.h'):
                (work / name).write_bytes(source.read(runtime.ARCHIVE[:-4] + '/' + name))
        publish = work / 'publish'
        (publish / 'lib').mkdir(parents=True, mode=0o700)
        library = publish / 'lib' / runtime.SONAME
        command = [compiler, *runtime.FLAGS, str(work / 'sqlite3.c'), '-o', str(library),
                   '-lpthread', '-ldl', '-lm']
        subprocess.run(command, check=True, timeout=600)
        header = library.read_bytes()[:20]
        runtime._need(header[:6] == b'\x7fELF\x02\x01' and header[18:20] == b'\x3e\x00', 'wrong_elf_architecture')
        dynamic = subprocess.run([readelf, '-d', str(library)], check=True,
                                 capture_output=True, text=True, timeout=15).stdout
        sonames = [line for line in dynamic.splitlines() if '(SONAME)' in line]
        runtime._need(len(sonames) == 1 and '[' + runtime.SONAME + ']' in sonames[0], 'wrong_soname')
        report = _candidate_probe(library)
        runtime._need(report['supported'] and report['sqlite_runtime_version'] == runtime.VERSION,
                      'candidate_validation_failed')
        manifest = dict(format='recognition-private-sqlite-v1', sqlite_version=runtime.VERSION,
            archive_url=url, archive_sha3_256=runtime.ARCHIVE_SHA3, compiler_command=command,
            compile_flags=list(runtime.FLAGS), library_sha256=hashlib.sha256(library.read_bytes()).hexdigest(),
            architecture='ELF64 x86-64', soname=runtime.SONAME)
        (publish / 'manifest.json').write_text(json.dumps(manifest, sort_keys=True, indent=2) + '\n', encoding='utf-8')
        library.chmod(0o500)
        (publish / 'manifest.json').chmod(0o400)
        # rename refuses replacing a nonempty existing version directory.
        publish.rename(destination)
    return manifest


if __name__ == '__main__':
    print(json.dumps(build(), sort_keys=True, indent=2))

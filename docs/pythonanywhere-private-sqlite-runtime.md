# Private SQLite runtime: build, stage, verify and roll back

This release provides an opt-in Linux x86-64 loader for standard-library
`sqlite3`, pinned to SQLite 3.54.1. It does not change application imports, SQL,
schema, driver, Python version, lifetime policies, authentication or activation.
No runtime is built or enabled by installing the repository files alone.

The live `/var/www/davidpoms_pythonanywhere_com_wsgi.py` is not in this repository
and was not accessed. The repository import convention is
`from src.api.app import app as application`. That module imports `sqlite3` on
line 3. The preload must precede that import and every other SQLite import.
If the hosting server already imported/mapped SQLite, startup rejects; it never
attempts replacement in an already-running process. A Bash pass does not prove
the hosting server's startup order.

## Local/disposable release validation

The portable focused tests simulate loading and exercise guards, real in-memory
SQL, exact inode text and application imports. They do not establish ELF loading.
On a separate disposable Linux x86-64 environment with the application test
dependencies, gcc and readelf, run the native test before production deployment:

```bash
RUN_PRIVATE_SQLITE_NATIVE=1 python -B -m pytest \
  tests/test_private_sqlite_runtime.py -q -p no:cacheprovider
```

The native test uses a temporary HOME, builds from the verified official archive,
starts fresh subprocesses, imports the app with file-database access forbidden,
and checks the normal process retains its original SQLite version. It does not
use either production database. This native test is skipped on Windows.

## Build (future separately scheduled owner operation)

Keep capture disabled and recognition NOT_ACTIVATED. Preserve the current WSGI
configuration, selected virtualenv, environment settings and release revision.
Do not run any migration, enrollment or activation command in this procedure.

From the updated checkout, in the application's existing Python environment:

```bash
python -B scripts/active/build_private_sqlite.py
```

For account home `/home/davidpoms`, the only published destination is:

```text
/home/davidpoms/sqlite-runtime/3.54.1/lib/libsqlite3.so.0
/home/davidpoms/sqlite-runtime/3.54.1/manifest.json
```

The script obtains the pinned amalgamation URL from SQLite's official download
metadata. Both the metadata and downloaded bytes must match SHA3-256
`92281c86e2957f9b9305890f9ac04204caa7b677cc868dc326d942689df28e30`.
If the pinned archive disappears from that page, it stops; it does not choose a
new version. Only `sqlite3.c` and `sqlite3.h` are extracted. gcc builds with
`-O2 -fPIC -shared -DSQLITE_THREADSAFE=1 -DSQLITE_ENABLE_COLUMN_METADATA`
and SONAME `libsqlite3.so.0`. It checks ELF64/x86-64, SONAME, actual loaded version,
JSON operators and all four exact-inode cases in a fresh child before publishing.

The manifest records version, official archive URL/hash, exact compiler command
and flags, library SHA256, architecture and SONAME. The version directory is
never overwritten. Staging is cleaned on ordinary failure; a hard kill may leave
an unpublished `.sqlite-build-*` directory. Do not adopt such a directory.
No system library, virtualenv, WSGI file or database is modified by the builder.

Check the manifest/hash without opening a database:

```bash
python -B - <<'PY'
import hashlib, json
from pathlib import Path
root = Path.home() / 'sqlite-runtime/3.54.1'
m = json.loads((root / 'manifest.json').read_text())
assert hashlib.sha256((root / 'lib/libsqlite3.so.0').read_bytes()).hexdigest() == m['library_sha256']
print(json.dumps(m, indent=2, sort_keys=True))
PY
```

Then test a fresh Bash child (this command's environment applies only to it):

```bash
RECOGNITION_SQLITE_LIBRARY=/home/davidpoms/sqlite-runtime/3.54.1/lib/libsqlite3.so.0 \
  python -B scripts/active/inspect_private_sqlite.py
```

Require `supported: true`, SQLite 3.54.1, both operators true, exact inode text
true, the unchanged standard-library extension, and only the intended mapped
library. No `LD_LIBRARY_PATH`, `LD_PRELOAD`, driver replacement or monkeypatch is
used. Inherited loader overrides are rejected.

## Stage the WSGI configuration (not performed by this release)

Use an approved maintenance window. Leave all existing database/key paths,
authentication/environment settings, activation settings and capture=0 unchanged.
Preserve the previous WSGI file separately before editing. The ordering is:

1. Existing environment configuration, plus the one explicit private-library path.
2. Add the existing repository root to `sys.path`.
3. Import/call the loader.
4. Import the application.

Insert this after existing environment/path setup and before the application
import, **not** after any import of Flask helpers that may themselves use SQLite:

```python
import os
os.environ['RECOGNITION_SQLITE_LIBRARY'] = '/home/davidpoms/sqlite-runtime/3.54.1/lib/libsqlite3.so.0'

# Existing project-root sys.path setup must already have run.
from src.api.sqlite_runtime import load_production_sqlite
load_production_sqlite()

from src.api.app import app as application
```

Keep only configuration and the loader call in WSGI; do not paste native-loading
implementation there. Do not catch loader errors or fall back to system SQLite.
Do not restart in-process after failure; correct the issue and obtain a fresh
worker. The retained handle lasts for that process only.

## Reload and verify the actual worker

After a separately authorized WSGI change, reload the existing web app. Inspect
its private error/startup log for `recognition_sqlite_startup` JSON emitted by
each new worker. Require the expected library/hash, version 3.54.1, standard
`_sqlite3` path, operators true, exact inode text true and supported true. Use PID
and log ordering to distinguish the new workers from old records. A missing
record, failure, mixed worker versions or a Bash-only success is not acceptance.
Check ordinary application health without invoking recognition operations.

The loader opens only `:memory:` for verification. It checks the library manifest,
hash and canonical owner-local path before/after loading, rejects symlinks,
hardlinks and group/world-writable runtime artifacts, and refuses any existing
SQLite import/mapping. Trusted ownership of native code and its manifest is the
boundary; these checks are not an independent signature or an anti-owner sandbox.

If startup fails, no migration/activation is permitted. Leave capture disabled.
Runtime startup verification grants no credentials, permissions, activation,
mutation or execution authority.

## Rollback before migration

1. Stop the attempted rollout; do not retry migration or activation.
2. Restore the saved WSGI file, removing the preload call and its configuration.
3. Reload the web app to replace preloaded workers; unloading inside a live
   process is not supported.
4. Verify ordinary health. For a worker-level version check, a temporary startup
   log statement after the normal application import can report only the version:
   `import sqlite3; print('rollback SQLite:', sqlite3.sqlite_version, file=sys.stderr)`
   (with the existing `import sys`). Expect 3.37.2 in each new worker. A separate
   Bash diagnostic alone does not prove worker rollback. Remove this temporary
   diagnostic after verification.
5. Leave recognition NOT_ACTIVATED and capture=0. Do not restore or edit either
   database merely because this runtime preload was rolled back.
6. Keep the private library until rollback has been verified. Afterwards the
   owner may remove only the exact inactive version directory; do not remove it
   while any worker still uses it.

This simple rollback applies to this pre-migration state. Once any later schema
migration commits, reverting to SQLite 3.37.2 may no longer be compatible; do not
reuse this procedure as a schema rollback or infer that a runtime rollback undoes
database changes. Uncertain outcomes require durable read-only inspection.

No production build, WSGI edit, reload, migration, enrollment or activation is
performed by the repository implementation or its tests.

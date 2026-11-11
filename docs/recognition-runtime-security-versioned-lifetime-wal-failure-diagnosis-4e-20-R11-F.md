# R11-F — WAL migration-validation failure diagnosis

## 1. R11-E baseline and diagnostic scope

[R11-E](recognition-runtime-security-versioned-lifetime-migration-isolated-validation-4e-20-R11-E.md)
implemented the lifetime migration but remained blocked: 23 focused tests and
57 subtests passed, with two WAL forced-termination/reopen subfailures. The same
failures reproduced outside the sandbox. DELETE recovery passed. Default policy
remained v1/120 seconds and no R12 measurement ran.

This slice changes no production code, migration, schema definition, policy or
existing recovery test. It adds two test-only diagnostic helpers and this report.
Toy SQL writes are confined to fresh disposable databases; the instrumented
migration probe uses the existing R11-E disposable fixture and child boundaries.

## 2. Exact failing path and connection lifecycle

Source: [R11-E test](../tests/test_recognition_runtime_authority_lifetime_policy.py),
`test_process_interruption_delete_and_wal()` and `_CHILD`.

1. A fresh registered `recognition-r11e-*` workspace is created under
   `C:\Users\dpoms\dmv-bus-stops`. Explicit target/control/synthetic-key paths
   are checked inside that root. The control file is `local-control.sqlite`.
2. A pre-migration populated v1 control snapshot is restored into the same file
   using SQLite backup. The restore connection closes before the child starts.
3. An isolated connection sets `PRAGMA journal_mode=WAL` (or DELETE) and closes.
   A separate administrative reader obtains the audit timestamp and also closes.
   The in-memory backup remains open; it is not a connection to the disk database.
4. The child runs the actual migration. Control BEGIN IMMEDIATE precedes the
   target BEGIN IMMEDIATE/query-only reservation. `admin.connect(write=True)`
   sets foreign keys ON and synchronous FULL on each write connection.
5. For committed=False, the test stops just after `_rebuild()` has removed
   staging, before the upgrade audit/final validation/control commit. For
   committed=True, it stops just after the control connection's real commit,
   before the public migration's postcommit verification/cleanup/result return.
6. The parent kills and reaps the child, then reopens control for writing. No
   surviving parent connection to that disk database is deliberately retained.
7. Reopening fails in [administration.py](../src/review/recognition/administration.py),
   `connect()`, line 63, at `conn.execute("PRAGMA synchronous=FULL")`. This is
   after `sqlite3.connect(uri, uri=True)` and foreign_keys=ON, but before the
   parent's BEGIN IMMEDIATE, schema checks or recovery assertions.

The control URI has the existing form
`file:///C:/Users/dpoms/dmv-bus-stops/recognition-r11e-<unique>/local-control.sqlite?mode=rw`.
There is no explicit checkpoint in this test or migration. Ordinary SQLite
connection-close and WAL checkpoint behavior remains enabled; no checkpoint was
added, forced or suppressed by this diagnosis.

The new capture identifies the extended error precisely:

```text
sqlite3.OperationalError: disk I/O error
sqlite_errorcode = 1546
sqlite_errorname = SQLITE_IOERR_TRUNCATE
```

No Python errno/WinError is supplied for this SQLite exception. The extended code
identifies the truncation error class, not which file or lower-level OS cause.

## 3. Migration state before the failing recovery boundary

[Migration diagnostic helper](../tests/recognition_runtime_wal_migration_diagnosis.py)
instruments the existing child source in memory. It performs only diagnostic
reads on the child's already-open control connection. It adds no database handle,
DDL, audit, commit or setting change. Reports contain booleans, counts, public
schema hashes and policy IDs, never credentials or key material.

Both captures used WAL and synchronous=2 (FULL), with only `main` attached:

| Captured property | Before commit | After confirmed commit |
| --- | --- | --- |
| Control transaction active | Yes | No |
| Staging absent | Yes | Yes |
| Exact successor authority definitions | Match | Match |
| Foreign-key violations | None | None |
| Protected rows unchanged | Yes | Yes |
| Original authority bytes unchanged | Yes | Yes |
| Original audit prefix unchanged | Yes | Yes |
| Added audit rows / typed upgrade audits | 0 / 0 | 1 / 1 |
| Authority policies | v1 only | v1 only |
| Full `check_control()` | Not a complete successor yet: upgrade audit intentionally absent | Passed on the actual committed connection |
| Ordered lineage | Upgrade not yet recorded | A -> T -> E -> L verified |
| Parent reopen in this instrumented run | `SQLITE_IOERR_TRUNCATE` at synchronous=FULL | Passed, full control check passed, upgrade present |

This confirms a valid committed migration state independently of the failing
last-client reopen. It does not claim that the precommit state was already a
valid committed successor, or that uncommitted recovery was demonstrated when
reopen failed. The public migration had not returned success at either kill point.

The successful instrumented committed reopen differs from R11-E's failure: the
diagnostic adds reads on the existing child connection after commit. Connection/read
ordering therefore affects reproducibility. No production change is inferred or
applied from that observation.

## 4. Minimal reproduction without recognition code

[Toy SQLite helper](../tests/recognition_runtime_wal_diagnosis.py) imports only
standard-library modules. Each case uses a new database with one table, one
original row and, for child cases, one UPDATE. There is no recognition package,
migration, schema replacement, authority, audit or application credential.

The child sets foreign_keys=ON and synchronous=FULL, begins IMMEDIATE, updates the
row and optionally commits. It signals its exact connection state, then the
parent kills/reaps it. Reopen uses the same URI/PRAGMA sequence as administration,
then tests BEGIN IMMEDIATE, expected read and an ordinary INSERT followed by
rollback. It does not repair the database or retry a failed SQLite operation.

| Probe | Reopen/read-write result | Observed row / error |
| --- | --- | --- |
| DELETE, clean close | Passed | Original |
| DELETE, killed uncommitted child, no other connection | Passed | Original: rollback preserved |
| DELETE, killed committed child, no other connection | Passed | Child value: commit preserved |
| WAL, clean close | Passed | Original |
| WAL, killed uncommitted last child connection | Failed at synchronous=FULL | `SQLITE_IOERR_TRUNCATE`, 1546 |
| WAL, killed committed last child connection | Failed at synchronous=FULL | Same exact error |
| WAL, killed uncommitted child, parent connection retained | Passed | Original |
| WAL, killed committed child, parent connection retained | Passed | Child value |

The retained parent connection had completed its SELECT and reported
`in_transaction=False`; it was an open connection, not a deliberately held read
transaction. This is a causal control for connection lifetime, not an approved
replacement for the original last-client-crash test.

The eight toy cases completed in approximately two seconds including process
startup and cleanup. Each child has an eight-second boundary wait and a bounded
five-second kill/reap path; there is no recognition lifecycle or unbounded pipe
drain. Every toy database and its sidecars were removed with its disposable root
only after connections/processes were closed/reaped.

## 5. DELETE comparison and integrity limits

DELETE-mode recovery preserves committed rows and rolls back uncommitted rows in
the toy control, matching R11-E's existing passing DELETE cases. This is useful
comparative evidence, not permission to abandon WAL.

Clean WAL reopen and the retained-connection controls also preserve expected row
values with synchronous FULL. The failing cases cannot establish successful
last-client recovery or absence of corruption: the SQLite operation fails before
the assertions can inspect recovered state. No failed recovery is labeled passed.

## 6. Environment and SQLite findings

Observed environment:

- Windows 11, build `10.0.26200`.
- Python `3.14.6`, MSC v.1944 64-bit AMD64.
- SQLite `3.50.4`; compile options include `MUTEX_W32`, `THREADSAFE=1`,
  `DEFAULT_SYNCHRONOUS=2`, `DEFAULT_WAL_SYNCHRONOUS=2`,
  `DEFAULT_WAL_AUTOCHECKPOINT=1000`, `DEFAULT_PAGE_SIZE=4096` and
  `DEFAULT_MMAP_SIZE=0`. No build/configuration was changed.

| Variable | Actual evidence / limit |
| --- | --- |
| Location | Fresh mode-0777 child directories directly under the verified repository root. Toy and migration probes reproduce there. No other filesystem/location was tested; location independence is not claimed. |
| Sidecars | Failed toy WAL cases leave a 32768-byte SHM file and WAL of 0 bytes (uncommitted) or 4152 bytes (committed). All are ordinary-readable after the child exits; reported file mode is 0666 and Windows attributes 32. |
| Migration sidecars | Before uncommitted reopen: WAL 0 bytes, SHM 32768. Before committed instrumented reopen: WAL 115392 bytes, SHM 32768. Files are readable and have the same reported mode/attributes. |
| Connection ordering | Clean close succeeds; forced death of the last child connection reproduces truncation failure; retaining another connection permits toy recovery. Added postcommit reads in the instrumented migration case also changed that case's result. |
| Open descriptors | Every killed child is reaped before reopen; ordinary toy no-anchor cases have no deliberately open parent database connection. In-memory backup connections are not disk handles. No general OS handle census was performed. |
| Checkpoint timing | No explicit checkpoint or autocheckpoint change. Exact internal SQLite checkpoint/truncation scheduling was not instrumented. |
| Cleanup timing | SQLite failure occurs before fixture file deletion. Roots are cleaned only after diagnostic reads and connection/process shutdown. Cleanup is not the triggering operation in the valid measurements. |
| Synchronous | FULL throughout the child transactions and reopen controls. The pragma is the first failing operation, not proof that the FULL value itself is defective. No lower guarantee was tested. |
| Journal mode | DELETE controls pass, clean WAL passes, last-client killed WAL reproduces. |

One retained-connection toy case denied an ordinary SHM file open with errno 13
while the SQLite connection remained open, then permitted it after SQLite recovery.
SQLite recovery itself succeeded in that control. This sharing observation is
not evidence of an ACL defect or justification for permission changes.

The precise VFS/OS truncation target and underlying cause remain unlocalized.
The evidence does not identify a fixed SQLite build, alternate filesystem,
permission setting or safe checkpoint workaround. None is invented here.

## 7. Diagnostic validation and scope

Commands run:

```powershell
.\.venv\Scripts\python.exe -B tests/recognition_runtime_wal_diagnosis.py
.\.venv\Scripts\python.exe -B -m tests.recognition_runtime_wal_migration_diagnosis
```

The first helper measured eight toy cases; the second measured the two existing
WAL migration boundaries and completed cleanup. Their process exit 0 indicates
successful diagnostic capture, **not** passing WAL recovery: errors are reported
as structured measurements. No pytest suite, lifecycle, R12, Z18, T or broad
regression was run in R11-F.

Two diagnostic-only setup defects were corrected before the valid captures:
the toy readiness file could be observed before JSON writing completed, so its
publication now uses a completed file followed by rename; the initial instrumented
probe's extra stderr file encountered WinError 32 during cleanup, so it now uses
DEVNULL exactly as the original test. These do not change the existing R11-E
test, migration, SQLite settings or security behavior. The final workspaces were
cleaned; no probe artifact remains.

Static validation includes both helper ASTs, document whitespace/local links,
source inspection, recorded production-source hashes and `git diff --check`.
Only the two test helpers and this report are added by this slice.

## 8. Decision A — WAL failure is test/environmental

**A — WAL FAILURE IS TEST/ENVIRONMENTAL.** More specifically, this is a
connection-lifecycle-sensitive SQLite/Windows-WAL truncation failure independent
of recognition schema mutation: the no-recognition toy reproduces the same exact
extended error, while the committed recognition schema passes complete validation
before termination. The evidence does not attribute it to a faulty migration
definition or demonstrate a recognition recovery-integrity defect.

This is a completed diagnosis at the requested migration-versus-environment
boundary, not a claim that the underlying Windows/VFS bug has been fixed. R11-E
remains blocked on its required recovery tests. No production approval follows.

## 9. Smallest separate correction and next boundary

**Next: 4e-20-R11-G — WAL validation correction and rerun.** Keep the correction
entirely in the test/environment boundary; no change to migration semantics is
justified. The acceptance prerequisite is a validation environment in which the
original last-client toy recovery succeeds with FULL and ordinary reopening,
followed by the unchanged migration interruption assertions.

No specific SQLite/VFS/filesystem substitution is established as a fix by these
measurements; it must be verified rather than guessed. Retaining a parent
connection is a demonstrated diagnostic control and may be kept as a separate
writer-termination case, but must not silently replace or declare success for
last-client/restart coverage. If a harness correction changes the intended
connection model, that distinction must be explicit and the remaining recovery
requirement must stay blocked until independently demonstrated.

Do not lower synchronous guarantees, switch away from WAL, suppress errors,
skip reopen, delete/repair sidecars, add retry/adoption or reinterpret journal
evidence as recovery authority. No workaround is applied by R11-F.

## 10. Explicit production blocks

Production/migration code and schema definitions are unchanged. No policy change,
v2 authority issuance/activation, G1, permissions change, hosted/production access,
recognition lifecycle, R12, Z18, T, broad suite, commit or push occurred.
Current/default authority policy remains v1/120 seconds.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED

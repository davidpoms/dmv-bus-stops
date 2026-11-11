# R11-G — WAL validation correction and isolated migration validation

## 1. R11-F baseline

[R11-F](recognition-runtime-security-versioned-lifetime-wal-failure-diagnosis-4e-20-R11-F.md)
reproduced `SQLITE_IOERR_TRUNCATE (1546)` without recognition code when the last
WAL connection was forcibly terminated. Clean WAL and DELETE controls passed.
The committed migration passed schema, lineage, foreign-key and preservation
checks before termination. The specific Windows/SQLite truncation cause remained
unlocalized, and [R11-E](recognition-runtime-security-versioned-lifetime-migration-isolated-validation-4e-20-R11-E.md)
remained blocked on its original recovery validation.

R11-G explicitly authorizes separating that environmental diagnostic from
migration correctness: validate normal WAL commit/close/reopen and, where writer
termination remains required, use a supported connection lifetime that avoids
killing the final WAL connection. This changes test topology only, not SQLite
durability, the migration transaction or production authority.

## 2. Validation defect

The original R11-E interruption test closed all parent disk connections, killed
the child writer and immediately reopened through `admin.connect(write=True)`.
The known environmental failure occurred at `PRAGMA synchronous=FULL`, before
the parent could inspect recovered schema/rows. It therefore coupled migration
correctness to an independently reproduced last-client WAL truncation failure.

DELETE coverage and synchronous FULL are retained. The environmental observation
is not reclassified as successful recovery or claimed fixed.

## 3. Smallest correction and files changed

Only [test_recognition_runtime_authority_lifetime_policy.py](../tests/test_recognition_runtime_authority_lifetime_policy.py)
and this document change in R11-G. No production, migration, validator, schema,
issuer, shared fixture or diagnostic-helper code changes.

### Normal WAL migration

New `test_clean_wal_migration_close_and_fresh_reopen()`:

1. Seeds the existing disposable populated v1 authority/attempt fixture and
   historical package chain; enables WAL on that disposable control database.
2. Captures original rows and historical manifests, then closes that reader.
3. Calls the real public migration owner with no parent disk connection retained.
   It must return success after its real commit, verification and clean context exit.
4. Opens a fresh write connection through unchanged `admin.connect()`, which
   executes synchronous FULL. Verifies journal mode remains WAL and synchronous=2.
5. Acquires BEGIN IMMEDIATE and verifies full control/schema/history, A/T/E/L
   lineage, exact protected rows and audit prefix plus one upgrade audit, original
   authority JSON/120-second interval, unchanged historical manifests, clean FKs,
   absent staging and a main-only connection. Closes normally.

### Writer termination and subsequent fresh reopen

Existing `test_process_interruption_delete_and_wal()` retains both before-commit
and after-confirmed-commit child kill points. DELETE retains its original
connection topology. For WAL only, an `ExitStack` owns a read-only parent control
connection through child termination and initial recovery. Its SELECT is completed;
the test asserts `in_transaction=False`, WAL and synchronous=2. It does not reserve
the writer, perform target DML, checkpoint, commit or modify any database row.

The same child still runs the actual migration and is killed/reaped at the same
boundaries. A separate parent write connection then requires synchronous FULL,
BEGIN IMMEDIATE and complete validation. The test now also compares **every**
original protected row and audit prefix: uncommitted work yields no upgrade audit,
while confirmed commit yields exactly one.

After that verification connection closes, the `ExitStack` cleanly closes the
retained WAL connection. A genuinely fresh connection must reopen successfully,
retain the selected journal mode and FULL, pass full validation and FK checks,
and reproduce the exact recovered row snapshot. No retained connection survives
the case or substitutes for this fresh reopen.

This proves writer-process termination with another SQLite client alive, followed
by clean final-client shutdown/reopen. It does **not** claim last-client forced-
termination recovery. The distinction is the explicit correction authorized by
R11-G; the latter remains separately diagnosed below.

## 4. Complete isolated migration validation results

Command:

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests/test_recognition_runtime_authority_lifetime_policy.py tests/test_recognition_runtime_schema_package_lineage.py -q -p no:cacheprovider --tb=short
```

Result: **24 passed, 59 subtests passed in 38.62 seconds**. No failures or skips.
This is the complete focused R11-E migration/versioning group plus required
lineage tests, with the additional clean-WAL case and corrected interruption topology.

Passing checks include transaction-scoped main staging and removal, exact schema
replacement, one migration audit, idempotency, policy constraints, historical
readers, protected rows, original credential clipping, deferred FK preservation,
post-upgrade package installation, rollback at six reserved fault boundaries,
commit uncertainty, concurrency, target query-only/reservation-through-commit,
DELETE interruption, WAL writer interruption and normal/fresh WAL reopen.

## 5. WAL results and separate environmental regression

| Scenario | Result |
| --- | --- |
| Real WAL migration, normal commit/context cleanup, fresh FULL reopen | Passed |
| Uncommitted WAL writer killed with parent connection retained | Original schema/rows; no upgrade audit; full validation passed |
| Committed WAL writer killed with parent connection retained | Complete successor; original rows preserved; one audit; full validation passed |
| All retained connections subsequently close, then fresh FULL reopen | Passed for both WAL cases; exact recovered snapshots preserved |
| Original DELETE termination cases and subsequent fresh reopen | Passed, preserving rollback versus durable commit |

The unchanged standalone
[environmental diagnostic](../tests/recognition_runtime_wal_diagnosis.py)
was also run separately. Its eight toy cases reported:

- DELETE clean/terminated-uncommitted/terminated-committed: all passed.
- WAL clean close: passed.
- WAL terminated last connection, before and after commit: both still reported
  `SQLITE_IOERR_TRUNCATE (1546)` at synchronous=FULL.
- WAL terminated writer with another connection retained: both passed.

These are structured diagnostic observations, not swallowed migration-test
exceptions or passing assertions about last-client recovery. The underlying
SQLite 3.50.4/Windows issue remains unresolved. The migration suite does not
catch/suppress that exception, lower synchronous, delete sidecars, retry, skip
reopen or silently switch WAL to DELETE.

## 6. v1 preservation

The focused group preserves normal and near-expiry v1 authorities and original
credential-clipped authorities. Immutable bodies, identities, timestamps,
source-audit relationships, genesis, attempts and other protected rows remain
unchanged. Full-length v1 remains 120 seconds; clipping remains the original
minimum. Historical schema hashes are not rewritten or reinterpreted by v2.

The new clean-WAL case explicitly repeats the row/history comparison after
migration and fresh reopen. Both interruption cases now compare all protected
rows, not just the authority row count.

## 7. v2 representation

The existing isolated R11-E tests pass for closed v2/300-second representation,
original credential clipping, immutable policy/version and malformed/unknown or
overlong policy rejection. These are synthetic storage DATA fixtures, not calls
to an issuer that grants process-local runtime authority. No new v2 fixture or
selection path is introduced by R11-G.

Ordinary issuance remains the unchanged v1/120-second implementation. No
production policy adoption or default change occurs.

## 8. Lineage, isolation and rollback integrity

All historical prefixes and permitted L positions pass the existing lineage
tests. Arbitrary predecessor/successor hashes, missing/duplicate/conflicting
audits, skipped prerequisites, unknown schema edges, altered SQL, stale packages
and invalid scopes remain rejected. The actual T/E installers still record raw
upgraded predecessor hashes when installed after L.

The production `check_control()` implementation and its main-only
`isolated_admin_control_required` predicate are unchanged. No staging object is
allowed at final validation/commit. The tests retain checks for TEMP/staging
rejection, copy preservation, rollback, foreign keys and unchanged target state.
No new migration or recovery mechanism is introduced.

## 9. Production-safety verification and static checks

Before validation, the five production source hashes matched the recorded R11-F
values. After validation they remain byte-identical: the migration owner,
authority schema/reader, administrative schema gate, lineage verifier and issuer
were not edited. In particular the issuer remains SHA256
`cf9cfcdb28208efabe78985f062f41684a5a09be0f6be5b8159faf298578a35c`.

The existing fixture proves explicit target/control/synthetic-key containment in
its freshly created registered disposable workspace; child processes repeat those
checks. No production configuration is inherited and no production/hosted
connection or credential is used. Migration key-content reads remain denied by
the existing focused test wrapper. All temporary workspaces are cleaned normally.

Static validation covers changed-test and inspected-source ASTs, focused schema
checks, new-document whitespace/local links, inspection of the complete test
changes, unchanged production-source hashes and `git diff --check`.

No recognition lifecycle, R12, Z18, T or broad suite was run. No production
database/data/schema/authority changed. Current/default policy remains v1/120 seconds.

## 10. Decision A

**A — R11-G MIGRATION VALIDATION COMPLETE.** The complete isolated migration
group passes, including normal WAL close/reopen and explicitly scoped writer-
termination recovery, with SQLite FULL and production semantics unchanged.

This supersedes R11-E's validation blocker under R11-G's authorized test topology.
It does not resolve or certify the separately recorded last-WAL-client forced-
termination behavior, approve production migration, or establish lifecycle viability.

## 11. Exact next boundary

**4e-20-R12 — bounded test-only v2 lifecycle feasibility measurement.** Use only
an isolated test authority and the corrected external harness. Do not activate
v2 in production. R12 was not run as part of R11-G.

## 12. Explicit production blocks

No production migration, v2 production issuance/adoption, G1, target execution,
permissions change, hosted/production access, lifecycle measurement, R12, Z18,
T, broad suite, commit or push.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED

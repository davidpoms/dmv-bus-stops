# R11-E — versioned-lifetime migration implemented; isolated validation blocked

## 1. R11-D baseline

The implementation follows the [R10 design](recognition-runtime-security-versioned-lifetime-compatibility-migration-design-4e-20-R10.md),
[R11-A main-staging amendment](recognition-runtime-security-versioned-lifetime-migration-design-amendment-4e-20-R11-A.md)
and [R11-C ordered-lineage rule](recognition-runtime-security-post-upgrade-schema-package-lineage-decision-4e-20-R11-C.md),
using the [R11-D kernel](recognition-runtime-security-post-upgrade-schema-package-lineage-implementation-4e-20-R11-D.md).
No new migration policy or recovery authority is introduced.

The migration and reader changes are implemented, but this slice is **not
approved**: forced-termination WAL recovery validation fails. Passing ordinary
migration tests is not a substitute for that requirement.

## 2. Isolated-environment proof

The new focused fixture allocates a fresh random `recognition-r11e-*` workspace
directly under the repository's verified writable root, using the previously
established creation mode. It uses the existing registered `DisposableWorkspace`
fixture. It asserts that the target, control and synthetic key paths all resolve
inside that exact fresh workspace. No deployment configuration is inherited.

The test-scoped directory adapter changes no shared fixture, ACL, global tempfile
setting or production path. Backups are in memory and restore only to the already
verified disposable control path. Existing synthetic enrollment/authentication,
proposal, approval and ledger fixtures provide storage references; no authority
issuance/coordinator/metadata-owner lifecycle is run.

Termination-test children receive only explicit disposable paths and a synthetic
clock. They independently check the root prefix and path containment before
connecting. There is no hosted connection, production database or production
credential. All child output is redirected to DEVNULL; waits and cleanup are
bounded, without pipe draining or retry loops.

## 3. Implementation changes and migration execution

- [runtime_authority_lifetime_policy.py](../src/review/recognition/runtime_authority_lifetime_policy.py):
  closed immutable policy resolver and explicit trusted-local migration owner.
- [runtime_activation_authority_schema.py](../src/review/recognition/runtime_activation_authority_schema.py):
  canonical policy-specific ceiling/overflow checks; historical original-credential
  clipping and prospective v2 source-audit cutover validation. Original schema
  definitions and the v1 default constant remain unchanged.
- [administration_schema.py](../src/review/recognition/administration_schema.py):
  select exact successor definitions only when the typed lifetime-upgrade action
  or identity is present. Full row/lineage/isolation checks remain mandatory.
- [runtime_schema_package_lineage.py](../src/review/recognition/runtime_schema_package_lineage.py):
  update its module description to reflect reuse by the explicit owner; no
  lineage algorithm or SQL transition changes.
- [test_recognition_runtime_authority_lifetime_policy.py](../tests/test_recognition_runtime_authority_lifetime_policy.py):
  disposable actual migration, storage compatibility, fault, concurrency,
  reservation and process-termination tests.
- [test_recognition_runtime_schema_package_lineage.py](../tests/test_recognition_runtime_schema_package_lineage.py):
  update the former dormant-schema assertion for newly implemented exact schema
  support, while still proving its minimal DATA binding fails runtime admission.
- This report.

The actual migration acquires control BEGIN IMMEDIATE, validates the original
control/history/current generation/physical scope and NOT_ACTIVATED state, then
acquires the target reservation and query-only mode. Integrity preflights use
separate readers as existing migrations require.

Under the reserved savepoint, it validates known incoming NO ACTION references
and dependent definitions; defers foreign-key checks without disabling them;
copies explicit columns/values to `main.recognition_authority_lifetime_upgrade_staging`;
verifies that copy; removes only known dependent guards/indexes; rebuilds the
authority table under its canonical name; copies original values back; restores
the exact successor/unchanged guards and indexes; and drops staging.

All original table values must match before the single typed upgrade audit is
appended. Complete final control/row/lineage validation then runs, followed by
protected-row/audit-prefix equality, fresh scope/target/time checks, manager-owned
control commit and committed read-only verification. Target reservation remains
held through commit. A lost commit/cleanup acknowledgement publishes no success.
No CLI, startup auto-migration, selection override or policy-adoption mechanism
is added.

## 4. v1 preservation

Isolated successful cases seed a full original v1 authority/genesis and an inert
historical attempt, with the original T/E package audit chain. Cases cover normal
120-second expiry, one second remaining at migration time, and 30-second original
credential/consent clipping.

Exact authority JSON, IDs, hashes, deadlines, source artifacts, all protected table
rows and the original audit prefix are compared before/after migration. Historical
authority/claim/attempt schema projections remain equal. The only added row is
the typed upgrade audit. Repeating the migration adds no second audit. Staging is
absent and the manager connection remains main-only after successful migration.

The historical-binding fixture is deliberately advanced before E is installed:
E's existing guard forbids clearing an enrolled profile outside its own transition
protocol. The fixture therefore seeds its historical binding first and installs E
normally afterward. No guard is dropped to bypass that restriction, and the
migration itself never changes generation, enrollment or activation.

## 5. v2 representation

In isolated fixtures only, successful migrations are followed by canonical
synthetic v2 authority/genesis/attempt storage graphs. These are DATA fixtures,
not issued process-local authority objects, production policy adoption or a
production v2 issuer. Valid v2 uses the closed 300-second ceiling; a credential-
clipped v2 uses 30 seconds. Original source-artifact and credential checks execute.
The historical reader requires original v2 consent/confirmation/consumption/issue
ordering strictly after the independently verified L cutover, with issue time no
earlier than cutover.

Unknown/null/boolean policies, v1 intervals over 120, and v2 intervals over 300
reject in canonical/table checks. Immutable UPDATE/DELETE guards reject changes.
The test isolates table CHECKs from the live scope trigger only inside its rolled-
back synthetic SQL probe; production guards remain installed and unchanged except
for the explicitly reviewed policy/cutover predicates.

Ordinary `_body()` issuance remains unchanged: v1 with issue+120 clipped by the
original step, confirmation, primary and session expiries. No argument or
configuration permits ordinary v2 selection.

## 6. Schema-package lineage

Existing pre-L packages keep their original recorded hashes. Another successful
isolated case invokes the actual existing T and E installers after L, verifies
the resulting A/L/T/E sequence and checks that T recorded the real upgraded raw
predecessor hash. The established lineage tests cover all allowed orders/prefixes
and rejection of missing, conflicting, skipped, malformed or arbitrary lineage.
No old audit is repaired or rewritten.

## 7. Control-check and target-boundary preservation

The body of the isolation predicate remains unchanged:

```python
require(len(conn.execute("PRAGMA database_list").fetchall()) == 1,
        "isolated_admin_control_required")
```

Full `check_control()` runs before mutation and after the successor DDL and audit
are complete. It is never bypassed. Unexpected staging or an initialized empty
TEMP schema rejects. Success requires no staging object and a main-only manager
connection. Successor recognition is exact-definition selection, not an object
allowlist or relaxation of schema integrity.

The passing reservation test checks the target transaction/query-only state at
control commit, rejects any target commit, and traces no target INSERT, UPDATE,
DELETE, DDL or COMMIT. All test teardowns compare unchanged target dumps and
writer/context registries. No writer or execution capability is created.

## 8. Rollback/failure results and remaining blocker

Passing isolated fault tests cover staging creation, parent removal, scope-trigger
creation, staging removal, audit insertion and final validation. Each restores
the exact original schema/rows/audit prefix. Silent commit no-op is rejected and
rolled back; a confirmed commit followed by a synthetic lost acknowledgement
raises without success and leaves a complete inspectable successor. Concurrent
calls produce one installation, one idempotent result and one upgrade audit.

The forced-process-termination test reaches the reserved precommit boundary and
confirmed-commit boundary in DELETE mode and verifies original/complete successor
state, respectively. Both WAL cases fail while reopening the disposable control
store after the terminated child:

```text
admin.connect(..., write=True)
  -> conn.execute("PRAGMA synchronous=FULL")
sqlite3.OperationalError: disk I/O error
```

That failure prevents validating WAL recovery for either committed or uncommitted
state. It occurs in the post-termination inspection connection, not a normal
migration success return. Its cause is not established as a migration defect or
an environment defect. A targeted run outside the sandbox reproduced it, so it
must not be attributed to sandbox restrictions alone.

No checkpoint, sidecar deletion, journal workaround, permissions change, automatic
retry, adoption or recovery authority was introduced. Required WAL coverage was
not removed, skipped or converted to a passing assertion. Recovery safety remains
unproven and blocks approval.

## 9. Focused test results

Focused command:

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests/test_recognition_runtime_authority_lifetime_policy.py tests/test_recognition_runtime_schema_package_lineage.py -q -p no:cacheprovider --tb=short
```

Latest complete focused run: **23 passed, 57 subtests passed; 2 WAL subfailures,
29.60 seconds**. The two failures are the WAL committed=False/True cases above.

Targeted interruption-only run outside the sandbox: **1 passed, 2 subtests passed;
the same 2 WAL subfailures, 13.76 seconds**. No lifecycle or broad suite was run.

Earlier fixture failures were corrected without changing security behavior:
seeding a historical binding after the E guard, setting the test clock before a
newer package audit, unwrapping a deny-only SQL fault proxy for real identity
observation, allocating TEMP through a read-only connection, and expecting the
wrong rejection code for an intentionally incomplete lineage DATA binding.
The directly affected preservation/rollback tests passed after those corrections.

Static validation: changed-file AST parsing, whitespace/local links, unchanged
issuer source hash, unchanged isolation predicate, inspection of the complete slice
changes, focused SQL/schema checks and `git diff --check`. These checks cannot
replace the failing recovery validation.

## 10. Production-safety verification

No production/hosted database was opened or migrated; no production credential was
used; no production schema/data changed; no production authority was issued.
The existing fixture generates its own synthetic key; the migration tests deny
key-content reads. The issuer source remains SHA256
`cf9cfcdb28208efabe78985f062f41684a5a09be0f6be5b8159faf298578a35c`.
Current/default production policy remains v1/120 seconds.

## 11. Decision B and stop

**B — R11-E BLOCKED.** The migration is implemented and ordinary isolated cases
pass, but WAL post-termination recovery cannot be validated because reopening
raises `sqlite3.OperationalError: disk I/O error`. No successful WAL crash-safety
claim or production migration approval is made.

Stop before R12. The remaining boundary is isolation of this specific disposable
WAL reopening failure and demonstration of the unchanged required crash/commit
semantics. This report authorizes no workaround or recovery mechanism.

## 12. Explicit production blocks

No production migration, v2 production issuance, policy activation, G1, target
execution, lifecycle measurement, Z18, T, broad suite, hosted/production access,
permissions change, commit or push.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED

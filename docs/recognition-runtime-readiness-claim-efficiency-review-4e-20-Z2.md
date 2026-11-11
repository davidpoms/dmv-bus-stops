# 4e-20-Z2: bounded readiness/control-claim validation efficiency

Z2 changes only `runtime_activation_authority_schema.historical_claim_manifest()`.
Readiness and claim validation are not replaced, skipped or supplied by a caller.
Z remains unvalidated; no Z, coordinator regression or broad suite runs here.

## Trace and observation boundary

Issuer `_subject_for_owner()` calls the exact owner's protected readiness adapter,
then `local_readiness._assess_inventory()`. The latter calls
`approvals.schema.check()` -> `administration_schema.check_control()` ->
`runtime_execution_claim_schema.check_rows()`. Pending runtime operations also
use authenticated approval/proposal readers. These re-enter owner scope/history
validation, including `check_control()`, through the existing shared read view.

Claim row validation first reconstructs the original claim-schema migration
manifest. `historical_claim_manifest()` validates the authority migration via
`check_manifest_transition()`. That function independently verifies the installed
and predecessor manifests through attempt `authority_manifest()`, including
recognized attempt/V extensions, audits, installation, scope and predecessor.
The caller formerly reconstructed the already-verified predecessor projection
once more. With no additional exclusions, that result equals the just-verified
`subject['previous_schema_sha256']` exactly.

Z2 returns this verified immutable digest only for an exact native SQLite
connection already in a transaction, with no additional exclusions. It is a local
value from the same function invocation, not an exported observation, cached
claim, readiness assessment, owner callback or reusable capability. All checks in
`check_manifest_transition()` still run. Different exclusion sets, unreserved
calls and unknown adapters retain the original reconstruction and ownership hooks.
No schema rows or audit records are trusted merely because they supplied a digest:
the transition validator first recomputes and compares that digest authoritatively.

There is no intervening write/yield/transaction or mode change in this reader.
The native transaction gives all projections the same SQLite snapshot. No local
value survives to another call. Every later call revalidates, regardless of
process/thread, connection, reservation epoch, mutation, auth/MFA scope,
generation, activation or lifecycle changes. Existing owner guards and fresh
final validation remain unchanged. No PRAGMA or security-state read was cached.

## Claims and readiness still mean the same thing

Claim `check_rows()` continues to read and validate every stored claim's identity,
operation/proposal/ACK, profile/binding/generation, authentication records, physical
snapshot, exact 300-second lifetime, full lifecycle history and audit linkage,
plus foreign keys. The optimization returns only a verified schema manifest,
never any of those claim observations. Authority/attempt/transition row checks
and authoritative activation/readiness checks remain separate and fresh.

The Z failure's generic claim-validation stack does not itself demonstrate that
live claims are numerous or expensive: the matching readiness fixture has an
empty runtime claim population. It still performs claim-schema migration and
manifest validation repeatedly. A separate test acquires a real disposable claim,
records a valid CONSUMED schema-fixture event with existing immutable guards,
checks fresh disposition/history, and rejects lifecycle digest corruption.
It creates no handoff, execution completion or writer authority.

## Bounded measurement

Only `tests/test_recognition_runtime_readiness_claim_efficiency.py` is run.
The file has a 120-second hard watchdog including fixture setup/cleanup.
The comparison uses the same real protected proposal read owner and reservation
machinery, current session/primary credentials and approved-operation fixture.
It calls the real readiness inventory twice with the same inputs. The before
case restores only the exact pre-Z2 manifest reader; all other readers remain
real. Assessment contents match after excluding the assessment timestamp.

An initial test-harness attempt using a 3a cursor failed because that cursor
does not expose the `description` property required by the schema reader. No
production adapter was changed or forged to make it work. The existing protected
proposal adapter supports this inspection; this is not a metadata-owner or
coordinator performance benchmark and does not assert that Z now meets its deadline.

Measured readiness call (inclusive/exclusive times overlap across nested layers):

| Layer | Calls before / after | Inclusive seconds before / after | Exclusive seconds before / after |
| --- | ---: | ---: | ---: |
| readiness inventory | 1 / 1 | 3.4095 / 3.1060 | .0055 / .0053 |
| control validation | 49 / 49 | 2.8459 / 2.5460 | .1513 / .1491 |
| claim row validation | 49 / 49 | 1.7521 / 1.4705 | .2991 / .2628 |
| history validation | 48 / 48 | 2.9525 / 2.6540 | .2182 / .2199 |
| V historical manifest | 1,378 / 1,234 | 2.3012 / 2.0401 | 2.2205 / 1.9597 |
| claims manifest | 102 / 102 | .0807 / .0804 | .0807 / .0804 |

| Read category | Before | After |
| --- | ---: | ---: |
| SELECT | 12,434 | 11,474 |
| SELECT involving sqlite_master | 4,601 | 4,217 |
| SELECT involving audit table | 4,291 | 3,907 |
| claim enumeration | 49 | 49 |
| claim-history SELECT (empty claim population) | 0 | 0 |
| PRAGMA | 656 | 656 |
| connection opens inside inventory | 0 | 0 |

Read-category counts can overlap. PRAGMA breakdown is unchanged: 195 database_list,
300 foreign_key_check, 65 table_info, 48 application_id and 48 user_version.
The diagnostic retains counts and timings only, never SQL text, tokens, seeds,
row contents or key material. Disposable key verification remains in readiness;
no real deployment key or hosted configuration is used.

## Focused security coverage and limits

Tests prove required readiness/control/claim checks still execute; the exact
projection's duplicate reconstruction falls from three calls to two; unreserved,
adapted and additional-exclusion paths retain behavior; every next call validates
again after transaction/auth/MFA/mode changes; reservation epoch change rejects
an existing borrowed admission view; generation/activation corruption cannot be
hidden by a preceding read; changed emergency stop is visible; schema/audit and
real claim-history corruption reject. Corrupted memory fixtures restore exact
triggers so schema drift does not mask data-integrity rejection. A synthetic
authority codec fixture still accepts its original 120-second bound and rejects
121 seconds. No authority object is persisted by that test.

No lifetime, auth primitive, approval, readiness state machine, target physical
identity, mode/transaction owner, activation or final-validation semantics changed.
No metadata owner, target-entry insertion, writer, execution, seal or recovery
was entered. The remaining cross-reader validation is deliberately untouched;
this modest measured saving cannot establish that all Z phases fit in the
remaining authority lifetime. Z must be evaluated separately after approval.

No full/recognition/deployment/coordinator/authority/execution suite; no production
database, hosted resource, deployment key, commit or push.

Validation: the focused file passed **9 tests and 2 subtests in 21.26 seconds**.
After adding explicit zero INSERT/UPDATE/DELETE/CREATE/COMMIT assertions around
the inventory measurement, only that test was rerun: **1 passed in 34.47 seconds**
including its disposable setup and both measurements. Timing varies with host
load; no timing threshold or claim about Z's lifetime fit is inferred.
`git diff --check` passed. Z was not rerun.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED

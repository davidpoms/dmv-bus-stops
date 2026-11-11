# 4e-20-R6: test-only extended-lifetime feasibility boundary

## 1. R5 baseline and result

[R5](recognition-runtime-security-lifetime-measurement-rerun-4e-20-R5.md) obtained
two bounded fail-closed expiry traces, not a complete lifecycle. R6 authorizes
an explicit test-only 600-second authority experiment, while prohibiting production
behavior and schema/migration changes.

**BLOCK: the requested authority-only override cannot be implemented within the
unchanged persisted schema/validation contract.** The 120-second bound is literal
in issuance, canonical validation, SQL and historical graph reconstruction, not
an overridable test parameter. No override, lifecycle attempt or migration was
performed. This finding does not establish that 600 seconds is insufficient.

## 2. Inspected override boundary

| Existing code | Actual enforcement | Consequence for a 600-second test authority |
| --- | --- | --- |
| `runtime_activation_authority_issuance._body()` | `min(issued+120, original step/confirmation/primary/session expiries)` | Patching only the diagnostic assertion leaves source lifetime 120 |
| `runtime_activation_authority_schema.validate_authority()` | Exact lifetime-policy identifier, `issued < expires <= issued+120`, bounded issue time | A source body with a longer interval fails canonical validation |
| `runtime_activation_authority_schema.definitions()` | SQL `CHECK(issued_at<expires_at AND expires_at<=issued_at+120)` and issue-time range | A longer durable row fails even if a Python wrapper accepts it |
| Historical authority reader in that schema module | Exact reconstructed `expires == min(issued+120, original artifact/credential deadlines)` | Returning a longer source without updating historical semantics fails final graph validation |
| Attempt and target-entry validators | Exact expiry equality to the original source | Cannot independently extend later stages without rebinding the source |
| Dedicated lifecycle diagnostic | Asserts actual authority interval exactly 120 | Changing this assertion alone does not change any authoritative check |

The implemented policy ID is `recognition-runtime-authority-lifetime-120s-v1`.
No public/default or existing test-only parameter allows a 600-second authority
while retaining the exact current SQL contract. Installing alternate test DDL,
rebuilding schema definitions, disabling CHECK constraints or replacing exact
schema validators would cross R6's prohibition on schema/security-behavior changes.
No such exception is inferred from permission to override a test lifetime.

## 3. Rejected workarounds and isolation

No production source files, shared fixtures, global configuration, SQLite settings,
keys, permissions or schema are modified. No runtime hook or environment-variable
override is introduced. Ordinary application execution therefore has no new path
to an extended lifetime.

Changing only the observed authority expiry would fail durable validation. Slowing
the fixture's clock so 120 product seconds last 600 wall seconds would stretch
authentication/consent and other time checks too, alter clock behavior, and measure
a different system. Suppressing expiry checks or fabricating historical validation
would not be a genuine authority-only feasibility measurement. These approaches
are not used to manufacture completion.

## 4. Production/default proof

Read-only AST/source checks confirmed all current 120-second mechanisms above.
The following SHA256 values were recorded before this document was created and
rechecked afterward to establish no local modification during R6:

| File under `src/review/recognition/` | SHA256 |
| --- | --- |
| `runtime_activation_authority_schema.py` | `da87733958e116a89a4408b46a56b58673c8644b66bddee01b20c248ea87e2d1` |
| `runtime_activation_authority_issuance.py` | `cf9cfcdb28208efabe78985f062f41684a5a09be0f6be5b8159faf298578a35c` |
| `runtime_execution_attempt_schema.py` | `b46299ad3c902aa7f411a3ca8bb5fab5d9bc7afa3e08771c4c782881241bcbf8` |
| `runtime_target_entry_storage.py` | `1e329c9ed68226f430e68b43bb869de52e4eb124e105bee33bc364d4f2ea1ae1` |

The harness and existing diagnostic were likewise hashed and left unchanged.
This is verification against the current checkout, not a claim these preexisting
working-tree files equal repository HEAD. No deployment configuration, production
database or hosted resource was read. No persistent policy was changed.

## 5. Harness bound and run results

The corrected harness supports an explicit finite per-invocation timeout and
cleanup budget without changing its default 360/5-second values. A 600-second
authority experiment would need an explicitly larger parent budget that also
covers pre-authority setup, with the same bounded reap/output rules. No concrete
larger invocation was made because the source/schema conflict occurs first.

**Lifecycle attempts: 0 of at most 3.** No new authority was issued and no target
mode transition, entry INSERT, commit, postcommit validation or successful cleanup
was reached. There is no new failure code from a child because none was launched.
Existing R5 expiry traces are not relabeled as R6 measurements.

## 6. Complete trace and critical-path status

All R6 lifecycle stages are **UNMEASURED**: issuance, preparation, coordinator
admission, attempt creation/final validation, metadata-owner admission/final
validation, mode transition, target-entry INSERT/commit, reservation reacquisition,
postcommit validation and cleanup/result publication. No stage is assigned zero.

Total duration, non-overlapping critical path, authority age consumed and remaining
600-second headroom are not established. Nested earlier measurements cannot be
summed or combined into a substitute complete trace.

## 7. Candidate lifetime/security comparison

| Candidate | R6 complete-workload headroom | Additional maximum age versus 120 | Finding |
| --- | --- | --- | --- |
| 180 s | Unknown | +60 s | Insufficient evidence to select |
| 240 s | Unknown | +120 s | Insufficient evidence to select |
| 300 s | Unknown | +180 s | Insufficient evidence to select |
| 360 s | Unknown | +240 s | Insufficient evidence to select |
| 600 s | Unknown | +480 s | Intended test ceiling only, not a demonstrated requirement |

Actual lifetime must still be clipped by original credential/consent expiry.
The test request does not authorize extending those separate deadlines. No longer
ceiling substitutes for exact scope, original-holder, fresh physical/authentication/
approval/ACK/activation/dependency/stop/history/claim/control/readiness checks,
permanent duplicate fences, concurrency or uncertain-commit inspection. Existing
controls can mitigate larger intent-age exposure but do not prove a numeric choice.

## 8. Recommendation G and G-series disposition

**G - evidence remains insufficient.** Neither successful completion below 600
seconds nor failure despite a valid 600-second authority has been measured.
The existing architecture's viability and whether a modest increase makes G1
replacement unnecessary remain unresolved. No implementation or automatic G-series
continuation follows from this blocked experiment.

## 9. Exact next boundary and validation

The exact conflict to resolve before measurement is whether a **strictly isolated
disposable test schema/codec variant** may be authorized alongside the test-only
600-second issuer, with original credential deadlines, policy labeling and default
120-second behavior explicitly preserved. Such an exception is not authorized by
the current no-schema-change instruction and is not implemented here. Do not
substitute a clock dilation or skipped check. No production lifetime or migration
decision is made by identifying this boundary.

Only this document is added. Read-only default-contract/AST checks, before/after
source hashes, document whitespace/local links and `git diff --check` validate the
blocked result. No pytest or lifecycle diagnostic is run, because the requested
experiment cannot yet satisfy its stated constraints. No production code/schema/
migration, permissions, G1 producer/enforcer, target mutation, hosted/production
resource, deployment key, commit or push.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED

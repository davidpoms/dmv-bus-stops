# R11-D — post-upgrade schema-package lineage implementation

## 1. R11-C baseline

[R11-C](recognition-runtime-security-post-upgrade-schema-package-lineage-decision-4e-20-R11-C.md)
defines a closed ordered lineage using existing typed migration audits and exact
definition sets: A (authority), T (attempt), E (enrollment transition) and L
(prospective lifetime-schema upgrade). A precedes T and L; T precedes E. L occurs
at most once. Existing audit bytes and raw schema-hash meaning remain unchanged.

This implements schema/audit DATA verification only. It does not implement or
execute the lifetime migration, activate v2, issue an authority or alter the
current 120-second lifetime.

## 2. Existing implementation

T/E installers already record the actual previous/installed normalized schema
hashes inside their manager-owned transactions. They remain unchanged. Original
readers project later additive packages out and require direct prerequisite hash
equality; that original path remains in use when no L action/identity is present.

## 3. Files and changes

- [runtime_schema_package_lineage.py](../src/review/recognition/runtime_schema_package_lineage.py):
  new read-only ordered-edge kernel, typed audit/binding checks, exact definition
  comparison and historical projections. It accepts no caller-provided definition
  set, transition callback or replacement hash.
- [runtime_activation_authority_schema.py](../src/review/recognition/runtime_activation_authority_schema.py):
  route L-bearing authority/claim historical queries through the kernel.
- [runtime_execution_attempt_schema.py](../src/review/recognition/runtime_execution_attempt_schema.py):
  route L-bearing attempt checks and original-authority projections through the kernel.
- [runtime_enrollment_transition_schema.py](../src/review/recognition/runtime_enrollment_transition_schema.py):
  select the actual historical package boundary when L is present.
- [test_recognition_runtime_schema_package_lineage.py](../tests/test_recognition_runtime_schema_package_lineage.py):
  focused in-memory schema/audit DATA tests; no migration or lifecycle fixture.
- This implementation report.

The kernel includes exact R10 successor SQL **inspection metadata**, derived from
the immutable original definitions by replacing only the authority table's
policy-dependent constraints and scope guard. It is needed to distinguish a
reviewed successor from arbitrary SQL. It has no installer, migration owner,
issuer selection or configuration hook. Tests compile endpoint schemas directly
in memory; they do not execute a lifetime upgrade/rebuild or create authority rows.

Current `authority.definitions()`, canonical policy validation, original clipping,
ordinary issuance, package installers and `administration_schema.check_control()`
are not promoted to successor behavior by this slice. Complete schema support,
codec/historical lifetime support and isolated migration validation remain R11-E.
That step must reuse the same exact successor metadata rather than create a
second incompatible definition of L.

## 4. Historical packages

The no-L reader path retains its original equality/projection behavior. Focused
tests exercise A, AT and ATE and compare stored audits and schema dumps before
and after verification. For pre-L packages in an L-bearing graph, the kernel
replays their original exact definition state and checks their originally recorded
before/after hashes. No stored hash, package ID or row is rewritten.

The authority projection selects A's installation boundary, independently of
whether L preceded or followed later T/E packages. The claim projection selects
the state before A. A helper's returned dictionary/digest is detached DATA, not
authority; consumers obtain a newly verified result on each invocation.

## 5. Post-upgrade packages

The kernel supports AL, ALT, ALTE, ATL, ATLE and ATEL, in addition to original
valid prefixes. It starts from the exact known claim-installation baseline and
applies only the actual recorded, ordered package deltas. T/E contribute their
unchanged complete definitions. L replaces the authority definitions with the
closed successor metadata and cannot occur before A or occur twice.

Each edge's recorded previous and installed hashes must equal hashes recomputed
from the complete state before and after that edge. The endpoint must equal the
actual current complete object map. Thus a later T/E audit binds the real upgraded
schema, while L's own cutover hash remains interpretable after later T/E additions.
Raw `claims.manifest()` and installer hash capture remain unchanged.

## 6. Migration-audit linkage

Verification checks the administrative audit chain, canonical typed records,
unique matching migration ID/action pairs, subject shape, lowercase hashes,
installation UUID, integer generation, actor/reason/time and historical binding
canonical bytes/digest/scope. The original claim audit anchors the reconstructed
baseline and must precede A. Duplicate/mismatched root identities reject as well.

Unknown schema-migration records after the claim anchor are not treated as benign
intervening edges. Ordinary non-schema administrative events remain allowed and
covered by the audit chain. No package's claimed predecessor hash substitutes for
exact definitions and the independently checked earlier path.

The kernel is historical/schema infrastructure, not full runtime enrollment,
current authentication, deployment identity or row-graph validation. Existing
full control and runtime checks remain required. There is no cache, retained
observation or cross-ceremony evidence reuse.

## 7. Failure and uncertainty

Missing/duplicate/malformed audits, wrong identity/scope, skipped prerequisites,
out-of-order transitions, unrelated hashes, unknown/missing DDL, reverted original
definitions with a claimed L audit and partial states all reject. Empty TEMP
presence still rejects through the unchanged main-only connection requirement.

Every invocation reads current authoritative schema/audit DATA again. The focused
rollback test observes a transient unexpected table, rejects it, rolls back that
test-only DDL and then verifies the restored endpoint. It does not prove the
actual migration's crash/rebuild behavior; those tests belong to R11-E.

No writes, cleanup, retries, repairs, adoption or recovery happen in this kernel.
Uncertain durable lineage is rejected; inspection does not grant new authority.
Existing transaction owners retain all commit/rollback and reservation duties.

## 8. Focused validation results

Command:

```powershell
.\.venv\Scripts\python.exe -B -m pytest tests/test_recognition_runtime_schema_package_lineage.py -q -p no:cacheprovider --tb=short
```

Final result: **14 passed, 42 subtests passed in 1.79 seconds**.

A final correction materializes projection exclusions once, preserving one-shot
iterables. The affected cutover-position test, including generator exclusions,
was rerun alone: **1 passed, 6 subtests passed in 0.70 seconds**.

Coverage includes original prefixes, all three complete L placements and partial
prefixes; unchanged audit/schema snapshots; integrated historical reader results;
arbitrary previous/installed hashes; missing/duplicate/conflicting records;
malformed identities/types/scope; skipped transitions; package self-assertion;
unknown schema audits/DDL; stale original definitions; audit corruption; isolation;
fresh reads and test-only DDL rollback; SELECT/PRAGMA-only verification; empty
authority/claim/attempt storage and unchanged default issuance.

Initial runs exposed two fixture-only mistakes: inserting a minimal historical
binding after its live profile guard, and querying a target-only legacy table in
a control-only fixture. The fixture now seeds its synthetic historical binding
before extension guards and asserts that the target-only table is absent. No
production guard was removed or relaxed. The final focused run passes.

Static checks: AST parsing of changed Python files, exact successor delta/object
set and SQL compilation through the focused fixtures, new-file whitespace/local
document links, inspection of the complete slice changes and `git diff --check`.
No broad regression or recognition lifecycle test was run.

## 9. Production/default boundary

No production database was opened or changed. No persistent migration, target
access, v2 authority, policy activation, writer/execution grant or G1 occurred.
All fixture databases are in-memory and contain no runtime authority or business
rows; their minimal historical bindings cannot establish runtime admission.

Ordinary issuance remains v1/120 seconds with original credential clipping. Its
source SHA256 remains
`cf9cfcdb28208efabe78985f062f41684a5a09be0f6be5b8159faf298578a35c`.
The unchanged administrative schema gate rejects successor endpoint fixtures
with `administration_schema_mismatch`. The new compatibility path therefore does
not itself enable installing or using the future successor package through
ordinary administration. R11-E must separately complete that migration support.

## 10. Decision A and next boundary

**A — R11-D IMPLEMENTATION AND FOCUSED VALIDATION COMPLETE.** The closed lineage
rule is implemented and focus-tested without changing current policy or runtime
authority. This is not approval of a production migration or a complete lifecycle.

**Next boundary: 4e-20-R11-E — complete versioned-lifetime migration implementation
and isolated migration validation.** Do not execute it against production.

## 11. Explicit production blocks

No actual lifetime migration, production data change, v2 authority issuance,
permissions change, G1, target mutation/execution, Z18, T, lifecycle run, broad
suite, hosted/production access, commit or push.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED

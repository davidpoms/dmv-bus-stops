# R11-B — amended versioned-lifetime migration: blocked

## 1. R11-A baseline

[R11-A](recognition-runtime-security-versioned-lifetime-migration-design-amendment-4e-20-R11-A.md)
resolves [R11's TEMP isolation conflict](recognition-runtime-security-versioned-lifetime-compatibility-migration-implementation-4e-20-R11.md)
with transaction-scoped main staging. The remaining
[R10 design](recognition-runtime-security-versioned-lifetime-compatibility-migration-design-4e-20-R10.md)
requires supporting the original package with or without installed attempt and
enrollment-transition extensions, preserving existing historical hashes and
predecessor ordering, and leaving raw current manifests authoritative for current
schema. R11-B requires stopping before inventing another security decision.

## 2. Implementation status

Only this report is added by R11-B. No Python, schema, validator, issuer, migration
or test file is changed. Inspection found an unresolved migration-lineage case:
installation of an existing optional extension after the lifetime upgrade.
This is distinct from the resolved staging issue. It does not establish that an
upgrade with all extensions already present is impossible.

## 3. Transaction-scoped staging

The approved main staging design remains applicable: create/copy/drop within the
reserved migration transaction, remove staging before manifest computation and
final validation, and retain the query-only target reservation through control
commit. No staging object or migration was implemented or executed in this slice.

## 4. Isolation-control preservation

`administration_schema.check_control()` and `isolated_admin_control_required`
remain unchanged. No bypass, intermediate-schema allowlist, TEMP allocation,
connection substitution or reordered final check is introduced.

## 5. Existing-row preservation

No repository database was opened. Existing authority bodies, policies, timestamps,
digests, genesis, attempts, bindings, authentication and audit rows remain untouched.
The proposed migration's preservation is not claimed validated.

## 6. v1/v2 policy status

The current schema and canonical reader remain v1-only, with a 120-second bound.
Ordinary issuer `_body()` still uses the original minimum of issue time plus 120
and the original step, confirmation, primary and session expiries. No policy
resolver, 300-second constraint, v2 selection or real v2 authority is added.

## 7. Exact historical compatibility conflict

The inspected paths are:

| Existing source | Behavior relevant to the conflict |
| --- | --- |
| [Attempt migration](../src/review/recognition/runtime_execution_attempt_schema.py), `migrate()` | Records `previous = claims.manifest(control)` and the raw installed manifest in the immutable migration audit. |
| Same module, `check_manifest_transition()` | Requires the attempt audit's previous hash to equal the original authority-install audit's installed hash, with that audit earlier in sequence. |
| [Enrollment-transition migration](../src/review/recognition/runtime_enrollment_transition_schema.py), `migrate()` | Also records raw current previous/installed schema hashes. |
| Same module, `historical_manifest()` | Requires its previous hash to equal the original attempt-install audit's installed hash. |
| [Raw manifest reader](../src/review/recognition/runtime_execution_claim_schema.py), `manifest()` | Hashes the actual current normalized object map; R10 explicitly preserves that meaning. |

Consider the supported original authority package without attempts. Let S1 be its
original installed manifest. R10 upgrades it to U1, whose authority table/scope
guard differ. The old authority-install audit must retain S1. If the existing
attempt installer runs afterward, it records U1 as its previous hash. Its existing
predecessor test then requires S1 = U1, which is false.

Likewise, with attempts already present but no enrollment-transition extension,
the old attempt audit retains S2. After upgrading that schema to U2, a subsequent
transition installation records U2 as previous, while its predecessor check
requires S2 = U2.

R10 section 9 specifies inverse projections for **old** migration manifests from
the successor schema. That preserves extensions installed before cutover. It does
not specify the audit lineage for extensions installed after cutover: which typed
audit is their predecessor, which version their new recorded hashes describe,
and how cutover verification reconstructs the upgrade's installed map after later
known DDL. R11-A changes staging only and leaves these R10 requirements intact.

A global inverse projection does not solve the later case: the new extension
audit contains raw successor hashes. Replacing those with projected hashes would
change what the existing installer records. Accepting an intervening upgrade as a
new predecessor requires an explicit ordered lineage rule and corresponding
validation. Requiring all extensions before upgrade would narrow R10's expressly
supported combinations. Permanently blocking their later installation would
introduce an installation-order restriction not specified by the approved design.
None of these choices is silently selected here.

## 8. Focused inspection and static validation

Read-only inspection covered R10/R11/R11-A, authority schema/codec/history and
issuance, administrative isolation, attempt and transition migration/readers, and
their raw manifest calls.

A definition-only diagnostic compared normalized object-map digests before and
after changing a lifetime-dependent authority CHECK in a local Python copy of the
definitions. The hashes differed both with and without the unchanged attempt
package. This was a hash counterexample only, not an accepted successor schema;
no SQL, authority issuance or database migration occurred.

The exact incompatibility follows from the actual installer assignments and
predecessor equality predicates above. No production helper was patched or invoked
to manufacture authority or pretend that a complete migration passed.

Focused compatibility pytest tests were not added/run because implementation
stopped at the required pre-edit contract gate. No migration, rollback, synthetic
v2 clipping or end-to-end compatibility result is claimed. Inspected Python ASTs,
this document's whitespace/local links and `git diff --check` were checked.

## 9. Production/default verification

No production migration executed; no production data changed; no v2 production
authority issued. Current/default policy remains v1/120 seconds. No G1, producer,
writer, target execution, readiness or activation change is introduced. Existing
workspace changes remain preserved.

## 10. Decision B

**B — R11-B BLOCKED.** The remaining contract decision is the exact immutable
migration-audit lineage for known extensions installed after the lifetime upgrade.
R10's existing-history projection does not define that case. Implementation must
not choose new predecessor semantics or an additional installation restriction.

## 11. Boundary before implementation resumes

Resolve that specific lineage/ordering decision, including which schemas the new
extension audits bind and how upgrade verification handles subsequent known DDL,
without rewriting old audit hashes or changing raw current manifest meaning.
No implementation alternative is authorized by this report. R12 is not reached.

## 12. Explicit production blocks

No schema/migration/permissions changes, target DML/DDL, production/hosted access,
real authority issuance, v2 activation, G1, Z18, T, lifecycle, broad suite, commit
or push occurred.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED

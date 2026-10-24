# Slice E: readiness, writer contracts, receipts and delayed approval

Production authorization, execution and activation remain BLOCKED. No real
production writer capability was provisioned. All positive execution/activation
tests use an explicitly synthetic, newly created disposable workspace. Local
hashes and append-only history protect application behavior; they are not
protection against trusted deployment/database administrators.

## Simplified readiness alongside dormant Slice 7

Slice 7's signed authority/status/enrollment/activation model was inspected and
left unchanged as dormant/test-only infrastructure. `local_readiness.py` supplies
the local model appropriate to the trusted-administrator threat model, without
reinterpreting or stripping Slice 7 prerequisites.

Assessment verifies current installation/target/restore binding, actual target
and control identities, pinned target schema, exact operation/private/execution
schemas, approval/control schema, owner role/verified identity, configured MFA
and existing protected host key, local activation history, durable stop history,
known writer/boundary/recovery interfaces, compatible pending operations, and all
unfinished claims/seals/projections. Incomplete installation/rebind fails existing
target-control verification. Invalidated historical approvals are not pending
work. Unsupported synthetic pending contracts block the production readiness
candidate. Any provider-selection object is rejected, never adapted or substituted.

Results distinguish:

| Result | Meaning |
| --- | --- |
| READY_FOR_DEPLOYMENT | Installed code/configuration is a candidate for deployment rehearsal; listed host requirements remain unverified. This does NOT mean the deployed platform is verified. |
| READY_FOR_ACTIVATION | Current generation has explicit, recent rehearsal observations and passes local checks. Still not production authority or activation. |
| BLOCKED | Identity, MFA/key, schema, stop, compatibility or required infrastructure failed. |
| RECOVERY_REQUIRED | An unfinished claim, missing/conflicting projection or unverifiable committed outcome needs deliberate recovery/reconciliation. |

`code_ready`, `deployment_verified`, `deployment_status`, `activation_ready`,
scope and explicit BLOCKED production fields make the boundaries separate.
Disposable reports say `disposable-contract-assessment` and
`DISPOSABLE_REHEARSAL_ONLY`; their `deployment_verified` is always false even if
the fixture's activation contract is satisfied. A report is plain data and is
not accepted as an execution context.

Trusted deployment operators may record hashes of twelve named rehearsal
observations, reason and time in the existing administrative audit. The record
binds exact installation/target/schema/generation and daily/30-day backup/verified
restore signoff. It expires after 24 hours and cannot survive a target rebind.
This is a local trusted-host observation ceremony, not external attestation or
automatic validation of a hosting provider. No actual deployment evidence was
obtained during this slice; tests use clearly synthetic evidence references.

## Activation state, API and installation

Explicit append-only `recognition_local_activation` history preserves
NOT_ACTIVATED, ACTIVATED, SUSPENDED, DEACTIVATED and RECOVERY_REQUIRED, with legal
transitions, generation/target scope, actor/reason/time, readiness digest and hash
linkage. Recovery is also a derived readiness condition while claims/projections
are unresolved; the last administrative state does not conceal that condition.
A restore/rebind makes an older activation scope effectively NOT_ACTIVATED.

Activation requires current owner administrative session, activate-scoped recent
step-up, explicit action/reason and a current readiness assessment under the
control/target writer locks. Stop, unsafe pending state or unresolved recovery
prevents it. Deactivation/suspension likewise require their own scoped step-up and
append history/audit. Production activation attempts are audited and return
BLOCKED WITHOUT appending ACTIVATED, even if the report is ready.

Only the registered fresh disposable production-contract fixture can simulate an
ACTIVATED state. That state cannot enable a real ProductionOperationContext.
The independent `production_operations.activation_guard`, preclaim production
provisioning rejection, writer capability provisioning rejection and old
production authority guard remain enforced. Tests independently remove the first
guard through mocking and verify the next still rejects before any claim/mutation.
There is no force/environment/database flag or provider fallback.

The existing owner/session/CSRF/no-store blueprint adds GET
`/api/admin/recognition-control/readiness` and POST `.../activation`. POST accepts
only state, step-up token, reason and CSRF token; production activation returns
409 with an explicit blocked result. No fixture/context input is accepted.
The existing CLI adds `install-readiness` and authenticated `readiness` inspection;
it adds no activation bypass or arbitrary writer command.

Installation is explicit, idempotent and rollback-safe in the CONTROL store. It
adds one minimal activation-history table and its immutable/sequence triggers,
NOT_ACTIVATED genesis and an inactive stop genesis if absent. Slice A schema
checking accepts the exact optional extension. Target operation/award/Explorer
schemas are unchanged. Startup and assessment never migrate, create fallback
files or activate recognition. No real installation or deployment was performed.

## Supported writer provisioning and boundary

First Look and Geography still dispatch only to known `permanent.finalize`
branches through the SINGLE Slice C coordinator. Before every lease, final
verification rechecks exact operation/approval, target/schema/generation, supported
rule/policy/accounting, dependency READY, activation/stop and outstanding recovery.
The already-admitted operation's own durable claim is excluded from the check
for OTHER unresolved executions; it never grants permission to another operation.

The coordinator owns BEGIN IMMEDIATE, durable claim commit, reacquired writer
transaction and final checks. The historical writer regenerates only to COMPARE
against the frozen manifest; it cannot replace the population. It uses the leased
connection, validates the entire population and commits nothing independently.
Writer effects and evidence seal share one target commit. Any precommit failure
rolls back all writer effects. No active per-item quarantine is introduced.

One-use leases bind exact operation/family/digest, target, installation/generation,
claim, connection and protected final-verification identity. Direct operation ID,
raw context, role flag, browser capability/writer name, CLI request or production
authorization object cannot invoke a writer. Existing idempotency/uniqueness and
Explorer isolation remain unchanged.

`DisposableProductionExecutionWorkspace` is an obvious synthetic fixture: it owns
newly created files, cannot adopt an arbitrary existing target and is registered
through the existing fresh-workspace boundary. It permits the REAL historical
writers to exercise the NEW production operation/receipt contract, with simulated
readiness/activation and current owner authentication. There is no HTTP, CLI or
environment selector for it. The production context loader still produces only
admission descriptors; actual production writer provisioning STILL rejects.

## Historical receipts and current projection

`production_receipts.py` defines `recognition-production-execution-receipt-v1`.
Positive tests explicitly mark `execution_scope=disposable-production-contract-fixture`.
The receipt retains operation ID/digest, event/preparation IDs, approval ID/hash,
actor and approval reason, installation/target/schema/restore generation, family,
rule/manifest hashes, claim ID/hash, deterministic seal identity, execution clock
start/end, full frozen population/hash, exact successful accounting, actual writer
result, verified writer records and evidence hash. These are coordinator clock
timestamps, not a claim of measured execution duration. No authentication secrets
or signing keys are stored in evidence.

Actual records include the immutable private operation/manifest, claims or
Geography snapshots/awards/members/witnesses/identities and referenced rule. The
manifest retains the wider considered/report population and exclusion/qualification
facts. Accounting requires every authorized member exactly once, matching known
writer result; quarantine and other outcome lists must be empty.

The authoritative HISTORICAL evidence is the immutable target claim and seal,
including the full receipt/outcome snapshot, committed WITH writer effects. It
does not depend on the current projection row being present or correct.

No redundant projection table was added. Existing `recognition_operation_receipts`
and local decision/execution histories materialize the operation result after the
seal commit. Local AUTHORIZED history references the actual local approval ID/hash,
not a signed authorization artifact; EXECUTING/COMPLETED history and receipt hash
are projected together. The original envelope/frozen data never changes.
Old synthetic history/receipt formats remain unchanged.

Current original recognition is still stored in the existing verified immutable
claim/award tables used by existing readers. `effective_recognition` additionally
provides a deterministic original view from the full sealed receipt. Its current
correction overlay is empty; future VOID/SUPERSEDE/REINSTATE/GRANT_MISSING operations
can supply explicit overlays/new evidence without overwriting original claims,
receipts or historical seals. No correction issuance or deletion was implemented.

## Crash, projection failure and owner recovery

| Failure | Durable result and permitted response |
| --- | --- |
| Writer/seal commit, no projection | Actual outcomes retained; ordinary invocation reports RECOVERY_REQUIRED, never reruns writer. |
| Projection transaction interrupted before commit | Projection/history changes roll back together; same sealed evidence remains. |
| Owner retries projection | Separate owner/session/recent recovery step-up validates seal and inserts the identical derived receipt/history without writer invocation. |
| Projection already current | Deterministic, idempotent; no duplicate award, receipt or completion history. |
| Materialized receipt lost | Rebuild from original seal while preserving existing matching history. |
| Projection conflicts with seal/history | Explicit RECONCILIATION_REQUIRED; no overwrite and no writer retry. Readiness reports recovery required. |

Recovery-scoped step-up can bind verified HISTORICAL seal/operation/history when
a broken projection prevents the ordinary operation getter from reading it.
This exception applies ONLY to recovery scope, requires actual approval and
valid sealed writer evidence, and grants no approval/execution authority. A broken
approval/event/claim/seal cannot be repaired by trusting projection flags.
`production_operations.load_recovery_context` reconstructs an inspection descriptor
from that verified seal after process restart, even when the ordinary getter cannot
read a missing projection. It requires the current target/generation and grants no
permission by itself; the same coordinator enforces owner session/recent recovery
step-up. No old in-memory fixture capability is needed to rebuild the projection.
Conflicting derived content remains durable evidence of the reconciliation
condition; historical completion is not silently changed to failure.

Original Slice C crash/claim/commit fencing, stop linearization and concurrent
writer behavior remain. No cross-database atomicity is claimed: control approval
is an earlier commit, claim is target-local, writer/evidence is one target commit,
and projection is a separate recoverable target commit.

## Delayed approval policy

An administrative session remains absolute and approximately eight hours.
Sensitive approval requires a NEW TOTP step-up scoped to the exact operation,
with a ten-minute expiry bounded by remaining session lifetime, followed by a
one-use exact-operation confirmation valid at approval time. A fresh primary
email login is NOT required solely because the existing session is several hours
old. Slice A documentation/test expectations were updated for this explicit policy.
Initial MFA setup and opening a new administrative session still require recent
primary authentication; step-up does not extend any session.

Expired step-up or confirmation, changed operation/state/target/generation,
session expiry, logout, owner change, MFA reset and restore invalidate access.
A fresh step-up cannot revive an older expired/consumed confirmation. Confirmation
consumption and approval persistence remain one control-store transaction.

After approval, worker continuation still requires the ORIGINAL nonrevoked,
unexpired administrative session and current authorized actor; it does not require
a second human Execute action. If the session expires before admission, approval
history survives but no authority is renewed automatically. The owner must log in,
create an explicit new unclaimed revision/operation, review it, obtain fresh
step-up/confirmation and approve it. The old approval can be invalidated/superseded;
it cannot be rebound to a new session/generation or used for blind continuation.
Already-claimed work uses the separate owner recovery protocol, not reapproval.

## PythonAnywhere and backup/restore rehearsal boundary

PythonAnywhere remains preferred. It was not accessed, researched externally,
rejected or replaced. CODE/contract readiness here is proven only with disposable
local tests. Actual DEPLOYMENT readiness requires configured deployed files and
observed environment behavior. ACTIVATION readiness additionally requires the
deployed installation's current assessment and explicit owner ceremony; the
repository's final production guards still remain a separate closed milestone.

Slice F's disposable platform rehearsal must verify all twelve observations:
SQLite locking and journal/commit behavior; concurrent workers; filesystem
permissions; persistent control store; backup creation; backup restoration;
scheduled/background jobs; restarts; process lifecycle; protected environment/MFA
secrets; absence of startup activation; and the target writer lock. It must also
exercise the claim-commit gap, uncertain acknowledgements, missing/conflicting
projection and real process restart, without production data or activation.

Daily backups with 30-day retention must cover a coherent target/control set and
protected required host secrets. F must establish a real write barrier/coordinated
snapshot or equally explicit consistent-cut procedure; this code does not claim
atomic backups of separate databases. Verify restore, manifest/integrity and
physical/schema/installation identities, then explicitly advance restore
generation, invalidate pending approvals/authentication and rehearsal evidence,
and require NOT_ACTIVATED with no automatic execution. Never delete journals or
blindly retry an uncertain writer. No real backup or restore was performed here.

External signing/status/authority/enrollment registries, host attestation,
external activation services and trust roots remain dormant/test-only and are
NOT production deployment prerequisites under this threat model.

## Files, validation and remaining milestone

Added `local_readiness.py`, `production_receipts.py`,
`test_recognition_readiness_receipts.py` and this report. Changed `admin_auth.py`,
`administration_schema.py`, `operations.py`, `production_operations.py` (recovery
descriptor loading), `local_execution.py`, `admin_routes.py`,
the management CLI, the outdated Slice A step-up test and Slice A documentation.
Earlier working-tree changes were preserved. No packages were installed.

Tests cover simplified readiness, schema/identity/MFA/key/provider failures,
explicit activation/suspension/deactivation, independent production blocks,
First Look/Geography actual disposable writer outcomes, complete independently
hashed receipts/accounting, deterministic/idempotent projection, interruption and
missing/conflicting projection recovery, concurrency, delayed approval and its
expiry/revocation/state/generation cases. Existing A–D, 1–7, authorization, writer
and Explorer regression tests remain. Final results are recorded below.

Remaining deployment blockers are actual platform rehearsal observations,
coherent daily/30-day verified backups/restores, secrets/permissions and worker/
restart/storage verification. Remaining activation blockers are the deliberately
closed production activation and writer provisioning factories and the later
explicit reviewed deployment/activation milestone. Slice F must validate those
requirements on disposable deployed infrastructure; it must not infer permission
to activate production or turn the fixture into a production provider.

Required safety answers are all NO: readiness alone activating production;
startup activation; ordinary reviewer execution; browser arbitrary writer;
CLI approval bypass; expired step-up approval; old confirmation approving changed
operation; projection failure rerunning writer; completed execution replay;
production selection of a synthetic provider.

Validation results: final full pytest 1,053 passed, 3 skipped, 1,043 subtests passed;
broad focused E/A–D/legacy execution/activation/authorization regressions 264 passed,
210 subtests passed; final E-only run 34 passed, 4 subtests passed; final recovery
descriptor/production-operation/authentication run 99 passed, 42 subtests passed.
Tracked and new/previously-untracked touched-file whitespace checks passed. Full
validation blocked external socket connections and repository database access.

No production recognition executed; no production award created; no production
activation; no production keys created; no external trust infrastructure created;
no PythonAnywhere production access; no production database access; no external
service contact; no commit/push.

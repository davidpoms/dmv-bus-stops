# Slice G — Trusted-Admin Production Activation

This implements a guarded production-contract path. **Implementation and testing
do not authorize actual production activation.** No PythonAnywhere configuration,
production database, production key, production award or deployed activation was
accessed or changed. Actual deployment/activation remains operationally BLOCKED
until the outstanding prerequisites are established and an owner explicitly
completes the ceremony in a separately authorized deployment.

Earlier Slice A–F reports describe their historical closed milestones. This
slice supersedes their unconditional local production rejection only through the
existing administrative and coordinator contracts described below. It does not
enable the legacy signed production-authority API or synthetic providers.

## Threat model and inspected contracts

The pinned project owner, deployment/database administrators, deployed code and
host are trusted. Protection covers unauthorized web users, mistakes, stale or
wrong-target approvals, duplicate/concurrent execution, crashes and uncertain
commits. Hashes and immutable SQL histories are application integrity mechanisms,
not administrator-proof evidence. Direct trusted-administrator data/code changes
remain outside the threat model. No external signing key, authority-status
registry, trust root, host attestation or second authorization architecture is
introduced or required.

Inspected before implementation: A's installation/session/MFA/confirmation and
restore contracts; B's exact approval and atomic confirmation consumption; C's
fixed writer, claim/seal and recovery coordinator; D's restartable production
descriptor and its sole activation-guard caller; E's local readiness/activation
and production-format receipts; F's local backup/restore and unavailable hosted
evidence. The dormant signed Slice 6/7 coordinators and legacy authority boundary
remain separate and unchanged.

## Readiness and activation ceremony

The existing assessment checks exact installation/target/control identity and
schema, owner/MFA/protected key, stop history, unfinished claims and projections,
compatible pending contracts, current-generation rehearsal observations and known
fixed writer/recovery interfaces. G additionally binds pending operation,
approval and dependency state into the assessment and blocks stale pending
dependencies or mismatched approval bindings. Invalidated/superseded history is
not executable pending work. Stale pending approvals must be deliberately
reconciled; readiness does not repair or reapprove them.

Deployment observations still require all twelve existing named checks and expire
after 24 hours. They are trusted operator observations, not external attestation.
Readiness is data, never activation or writer authority. Positive test observations
are synthetic and do not establish PythonAnywhere compatibility.

Activation uses the existing owner API and control-store transactions:

1. Authenticate the pinned verified owner and open the existing eight-hour
   administrative session using TOTP. Obtain an `activate`-scoped recent TOTP
   step-up (at most ten minutes, bounded by session expiry).
2. POST `/api/admin/recognition-control/activation/confirmations`, with exactly
   `step_up_token` and `csrf_token`. Under control-then-target `BEGIN IMMEDIATE`,
   the server verifies the session, step-up, legal state and current readiness.
   It returns an opaque confirmation token and the readiness assessment.
3. Review that assessment and explicitly POST `.../activation`, with exactly
   `state`, `step_up_token`, `confirmation_token`, `reason`, `csrf_token`.
   `state=ACTIVATED` requires the confirmation token. Suspension/deactivation
   require their own scoped step-up and may pass a null confirmation token.
4. Under the same lock order, the server recomputes readiness and checks the exact
   current owner/session, token purpose, target/installation identities, restore
   generation, current activation-history state, expiry and readiness digest.
   Confirmation consumption, activation history and audit append commit in ONE
   control transaction while the target writer reservation remains held.
   Confirmation issuance/activation refresh server UTC after lock acquisition;
   expiry is not evaluated using a timestamp taken before a lock wait.

No new table is required. Activation confirmations reuse A's existing confirmation
store with a disjoint server-created purpose `activation:<installation UUID>`.
Ordinary operation approval cannot consume them, and operation confirmations
cannot activate. Only token hashes are stored/audited. A consumed token cannot
activate again; concurrent attempts serialize. An append failure rolls back token
consumption with the state/audit change. Lost acknowledgements are inspected via
readiness/history, not treated as permission to repeat a ceremony blindly.

The readiness fingerprint excludes only the assessment's observation timestamp:
time is independently checked for freshness and expiry. It includes deployment
observation identity, pending operation/dependency/approval bindings, stop history
and current assessment/state. Re-recording evidence, changing a dependency,
advancing generation or changing activation state invalidates the old intent.
No caller can submit an expected hash or choose these bindings instead of the
server recomputing them.

Production activation history has scope `trusted-local-production` and references
the consumed confirmation and its ceremony hash, plus actor, target/generation,
readiness hash, reason, time and previous history hash. A state name or database
boolean alone is insufficient. An old E fixture's simulated ACTIVATED state is
still insufficient for a real production descriptor.

## States and execution

The existing NOT_ACTIVATED, ACTIVATED, SUSPENDED, DEACTIVATED and RECOVERY_REQUIRED
transition graph remains. Genesis is NOT_ACTIVATED. Recovery-required state can
transition only to DEACTIVATED. Outstanding uncertain claims also derive a
recovery-required assessment, regardless of the last administrative state.
Rebind makes old-generation activation effectively NOT_ACTIVATED and invalidates
pending approval/session/confirmation authority. Startup never installs, enrolls,
activates, scans or executes work.

Suspension/deactivation are explicit owner actions with scoped step-up, reason and
audit; reactivation needs a new full activation confirmation. Emergency stop is
independent and checked before every new execution. It does not interrupt an
already committing writer; control-lock serialization preserves the existing
stop semantics. Neither an inactive stop nor readiness can activate production.

After a valid trusted-local activation, assessment reports `ACTIVATED`,
`PER_OPERATION_APPROVAL_REQUIRED` and, only while all execution prerequisites
remain satisfied, `FINAL_ADMISSION_REQUIRED`. These describe conditional paths,
not an unconditional grant. Unactivated and legacy synthetic scopes keep BLOCKED
production fields. Deployment evidence expiry or new unsafe pending/recovery
state blocks new admission even while the stored activation state remains active.

There is no Execute browser control, new writer callback, daemon or scheduler.
Existing `approve_and_execute` persists B's one-use exact confirmation/approval,
then uses D's server-loaded descriptor and C's same final admission coordinator.
Activation itself never executes pending work. The existing explicit bounded
`scan-approved` entry can discover already-approved work after restart; it uses
the original approval's still-valid owner session and all normal final checks.
Expired approval sessions are not renewed or rebound automatically.

## Production writer provisioning

Only historical First Look and Geography `finalize`, with the exact existing
rule, frozen manifest and atomic/no-quarantine policy, are supported. Explorer,
live sealing, discrepancies and future correction issuance are not newly granted.

`production_operations.activation_guard` now requires live coordinator
transactions and valid consumed local ceremony evidence. Production still cannot
be enabled by an environment flag, CLI option, caller-supplied context/provider or
raw state name. The preclaim boundary independently checks ceremony evidence;
removing a single guard does not turn E simulation into production permission.

After durable claim commit, C reacquires the target writer transaction and repeats
all final checks. Only that protected boundary supplies the one-use admission
tuple and live control connection to `writer_boundary._local_lease`. For a D
production descriptor, lease provisioning independently verifies the registered,
consumed descriptor, production claim scope, control transaction, current
installation/target, ceremony and full final approval/dependency/readiness checks.
It matches the checked operation/manifest to the durable claim. Possession of a
descriptor, operation ID, claim or readiness report alone cannot mint a lease.
Production rechecks obtain current server UTC time before claiming, after
reacquiring the target transaction, and at lease issuance. They do not preserve an
expired approval session or rehearsal observation using an earlier request time.
The clock is not a configuration/environment/provider option; tests patch it only
inside synthetic fixtures and explicitly isolated test subprocesses.

The capability binds the exact connection, target, operation/family/manifest,
claim, generation and final-verification identity. Production claims and receipts
also retain the exact activation-history hash, rechecked during provisioning and
bound into the capability through the claim hash. It is consumed once and revoked
on scope exit. The fixed historical writer uses that same transaction and commits
nothing independently. All writer effects and the durable seal share one target
commit. Whole frozen population validation, unique lifetime claims, Geography's
frozen evaluation/membership, Explorer isolation and no active per-item quarantine
remain unchanged.

Legacy `authority.provision_production_authority()` and the old
`Authorization(environment='production')` writer guard still reject. G does not
provision that obsolete high-assurance architecture; it uses C's existing local
capability path. Synthetic Slice 4–7 providers cannot substitute for this ceremony
or capability. The original disposable fixture path remains explicitly isolated.

## Receipts and recovery

G claims/receipts use execution scope `trusted-local-production`; E's
`disposable-production-contract-fixture` receipts retain their historical scope.
Both use E's same verified production-format evidence, accounting and projection
code. The receipt format and target/control schemas are unchanged. Recovery binding
and missing-projection reconstruction recognize both exact scopes.

An unfinished durable claim remains fenced. Missing/uncertain seals never cause
blind retry. Owner/session/recovery-scoped recent TOTP inspection can verify a
committed seal and project its existing receipt without calling a writer. A
no-effects claim can be terminally fenced; residue/conflicting projection requires
manual reconciliation. Completed evidence is idempotent across new descriptors
and process restarts. Target/control commits remain separate; no distributed
atomicity or deliberate both-store rewind protection is claimed.

## Configuration and operational prerequisites

Keep `DMV_BUS_STOPS_DB` explicit, existing and absolute. Set both
`RECOGNITION_ADMIN_CONTROL` and `RECOGNITION_ADMIN_KEY_FILE` for administrative
operation. All three paths must be absolute and distinct. The control file must
already have its explicitly installed compatible schemas and pinned bindings.
The existing key must contain valid Fernet material, be a regular non-symlink file
and, on POSIX, have no group/other permission bits. Restrict parent directories,
keep private files outside static/source mappings and separately protect secret
recovery. No key creation or secret-file/log/configuration change is added.

No package, startup migration or install command is added. Retain explicit A/B/D/E
installation and preview/rebind procedures; changed pinned schemas must be
reconciled deliberately. HTTPS cookies, persistent Flask secret, genuine owner
email login, MFA enrollment, revocable sessions and CSRF remain required. During
deployment verification keep capture disabled and do not perform activation.

PythonAnywhere remains NOT ASSESSED. Before actual activation establish the
deployed release/WSGI, intended paths and physical/schema compatibility, permissions,
real SQLite concurrency/locking, process/task/restart and crash recovery, protected
secrets/logging and an enrolled pinned owner. Establish daily verified coherent
target/control backups, 30-day retention, protected key recovery and a manual
restore/rebind drill preserving independent control generation. The existing pilot
backup script is single-database; F's paired/retention helper is test-only, not an
installed production backup service. Inspect actual schedules; none is introduced
by G. Record only observed, current-generation deployment evidence, never synthetic
test evidence, and resolve pending incompatibility or recovery before ceremony.

## Validation and release boundary

Focused tests cover successful activation, exact/expired/wrong-purpose confirmation,
readiness and dependency changes, missing/expired step-up, wrong owner, restore
generation, stop, suspension/deactivation, atomic audit/history and concurrent
activation. They also exercise real D production descriptors against fresh owned
synthetic files, First Look/Geography receipts, approval-driven execution, duplicate
concurrency, fresh-process continuation, unfinished-claim fencing and every C
crash boundary. HTTP tests exercise owner/CSRF/strict fields; CLI/environment and
synthetic-state tests verify there is no shortcut. Existing startup, writer and
A–F regressions remain part of validation.

All positive activation/writer tests use synthetic, newly created disposable
files, identities and test-only key material. They do not activate a deployed
installation or produce production awards. Test runs block external connections
and repository database access; fresh worker probes restrict SQLite to their
fresh synthetic root. No production secret is copied into source, logs, HTTP
responses or fixtures. No tests select an arbitrary operational database.

Validation:

- Final focused G suite: **36 passed, 4 subtests passed**, 29.57s.
- Relevant A–F, historical writer, startup, execution/recovery and dormant-provider
  regressions: **293 passed, 175 subtests passed**, 107.24s.
- Additional G plus D/E checks after the clock hardening: **93 passed,
  27 subtests passed**, 79.16s. The final focused run includes the additional
  activation lock-wait expiry test.
- Final stable-tree full suite: **1097 passed, 3 skipped, 1053 subtests passed**,
  276.66s. This supersedes the earlier run that overlapped the clock change.
- Tracked and new-file whitespace checks passed; Git's LF→CRLF notices are
  informational.

Actual production authorization, execution and activation remain **BLOCKED by
unestablished deployment prerequisites and the absence of an authorized deployed
ceremony**. Code now supports that ceremony conditionally; it no longer rejects
every correctly activated trusted-local production descriptor unconditionally.
No production activation or provisioning was performed. No external infrastructure,
production key, production award, commit or push was created.

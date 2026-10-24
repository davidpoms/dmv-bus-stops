# Slice 7: production readiness and installation activation contract

Production is unprovisioned and blocked. Readiness is not activation. The only
implemented state provider is a fresh disposable interface-double workspace; its
`READY_FOR_ACTIVATION` and `ACTIVATED` results describe that workspace only.
Every assessment exposes `production_ready=False`, and every activation state
exposes `production_admitted=False`. No application writer consumes these results
as authority. There is no production loader, registration hook, callback provider,
environment flag, database flag, Flask-role path, or production activation factory.

## Actual Slice 1–6 interfaces and prerequisites

`activation.PREREQUISITES` is the machine-readable inventory. Each check records
its interface, boundary, outcome, observed native state and non-secret evidence hash.

| Prerequisite | Existing interface / required observation |
| --- | --- |
| Production trust root and protected signing keys | `trust.configuration`; only `SyntheticTrustProvider` exists. Production configuration must be independently provisioned. |
| Signed authority status | `status.verify_current_status`; requires authenticated current status, signature and freshness. |
| Protected status continuity | `status._verified_status_transaction`, Slice 6 target-retained floors; local SQLite alone cannot prove protected rollback continuity. |
| Target enrollment | `enrollment.verify_record` / `verify_target`; exact immutable enrollment reference and generation. |
| Enrollment continuity | `enrollment._observe`; synthetic registry/incarnation witness is not a protected production registry. |
| Exact physical target | `authorization.target_identity`, enrollment observation; OS/process fencing and restore detection remain external. |
| Dependencies | `dependencies.recheck`; only READY is safe. STALE, INVALID and VERIFICATION_FAILURE block. |
| Rule/policy versions | `permanent.DEFINITIONS`, `execution.POLICY`, `operations.ENROLLED_CONTRACT`; only atomic historical policy is supported. |
| Operation integrity | `operations.get_operation`; immutable event, manifest, enrollment and history bindings. |
| Authorization | `trust.verify_historical_authorization` / `verify_authorization_time`; signed exact operation plus current admission status. |
| Execution claim/journal | `execution_schema.check_schema` / `execution.execute_operation`; immutable claim, evidence seal and terminal projection. |
| Writer boundary | `writer_boundary.production_guard` / `acquire`, `permanent.finalize`; production authorization still rejects. |
| Recovery | `execution.reconcile_operation`, separate `SyntheticRecoveryContext`; no ordinary execution retry privilege. |
| Emergency stop | `execution.set_emergency_stop` / `clear_emergency_stop`; separate durable execution control. |
| Trusted time | Existing APIs accept explicit UTC; no production clock provider exists. |
| Required finality | `live_first_looks.seal_pending` requires a finality guard. Slice 6 supports historical issuance only; this slice cannot qualify live finality. |
| Provider separation | `trust.configuration` and registered synthetic contexts reject production use. |
| Production provisioning | `authority.provision_production_authority` unconditionally rejects. |
| Startup | `RecognitionGate`, `DISABLED`, API issuance defaults; imports do not activate, migrate, enroll or provision. |
| Database selection | `src.api.deployment.configured_database` requires an explicit absolute target; there is no fallback. |
| Explorer isolation | Historical dispatch uses `permanent.finalize`; Explorer processing/schema remain separate and unchanged. |
| Schema/version compatibility | Event, operation, private and execution schema checkers; deployment must attest the exact enrolled schema. |
| Administrative identity and MFA | No production executive/TOTP interface exists. An issuance grant or application role is not administrative authentication. |
| Protected activation storage | Requires an installation ledger outside the mutable recognition target, with independent continuity and fencing. |
| Deployment controls | Reviewed deployment, backup/restore policy and continuity controls remain external. |

REPOSITORY-VERIFIABLE means the interface, fixed policy/default or schema contract
can be inspected and tested here. `_repository_checks` checks contract availability,
fixed supported policy/defaults and no-fallback selection without opening a target.
It does not infer deployment correctness from function existence. Even these rows
need runtime evidence; production currently reports them unverified. The readiness
module never opens an actual recognition database or invokes a recognition writer.

EXTERNAL-INFRASTRUCTURE-REQUIRED includes protected signing-key storage, production
trust-root provisioning, authenticated executive identity, TOTP/MFA, authenticated
signed-status delivery/registry, protected status rollback continuity, protected
enrollment registry and independent incarnation/restore signal, exact deployment
target observation and host/process fencing, trusted time, protected installation
audit continuity, backup/restore policy and production deployment controls. Live
issuance additionally requires an approved finality provider/policy. None is proven
by a synthetic provider, local file identity, database row or successful pytest run.

## API and result semantics

`assess_production_readiness(installation=None, evidence=(), generations=None,
trusted_now_utc=None)` returns immutable canonical JSON and its SHA-256. It performs
no writes. For the default/unrecognized production installation it always returns
BLOCKED, with each missing runtime prerequisite marked
EXTERNAL_PREREQUISITE_UNVERIFIED. Caller evidence cannot change that result.

Each check has SATISFIED, BLOCKED, EXTERNAL_PREREQUISITE_UNVERIFIED,
CONFIGURATION_ERROR or INTEGRITY_FAILURE. Only all-SATISFIED checks yield
READY_FOR_ACTIVATION. Expired, future, duplicate, malformed, inconsistent or unsafe
native observations fail closed. A SATISFIED label paired with STALE dependencies,
MISMATCH enrollment, FALLBACK database selection or SYNTHETIC production separation
still blocks. There are no warning outcomes.

The approved test-double interface consists of `InterfaceEvidence` records with a
prerequisite, outcome, native observed state, observation/expiry timestamps and
evidence digest; trust/status/enrollment/deployment generation numbers are explicit.
Only registered `SyntheticActivationWorkspace` instances accept them. This models
observations returned by future reviewed real adapters, not implementations of those
adapters. Passing `SyntheticTrustProvider` as an installation does not qualify.

`get_activation_state()` returns production NOT_ACTIVATED. State reads in the
disposable harness verify the complete ledger and fail on corruption; they never
create files or schemas. Assessment may say READY while state stays NOT_ACTIVATED.
READY is therefore assessment status rather than a persisted activation transition.

## Ceremony and state model

`activate_production`, `deactivate_production`, and `suspend_production` expose the
narrow future administrative call boundary. Production calls return BLOCKED.
In the disposable harness each call requires a registered assessment and an explicit
signed ceremony, not a bool, role or approval row. `ceremony_payload` constructs
public signing data only; it neither signs nor grants authority.

The domain-separated Ed25519 verification uses Slice 4 `trust.verify_signature`,
strict JSON/time/key validation and an explicitly designated synthetic administrative
identity. It does not repurpose an issuance grant as real executive authentication.
The payload binds action, ceremony UUID, installation UUID, administrative key/actor,
assessment digest, trust/status/enrollment/deployment generations, expected sequence,
prior state/hash, issued time and expiry. Production will require authenticated
executive/MFA attestation from an independently reviewed identity provider before
any production implementation of this boundary can exist.

Transitions:

| Action | Prior state | New state |
| --- | --- | --- |
| activate | NOT_ACTIVATED, DEACTIVATED, SUSPENDED | ACTIVATED, after fresh readiness |
| deactivate | ACTIVATED, SUSPENDED | DEACTIVATED |
| suspend | ACTIVATED | SUSPENDED |

Safety suspension/deactivation require the signed administrative ceremony but not
successful readiness. Activation rechecks evidence expiry, repository contracts and
the exact prior state under a SQLite writer lock. Replaying an applied exact ceremony
returns ALREADY_ACTIVATED / ALREADY_DEACTIVATED / ALREADY_SUSPENDED without another
row, including after ceremony expiry. A new valid activation ceremony for an already
active installation also returns ALREADY_ACTIVATED. Stale or conflicting ceremonies
block. A failed/unverifiable write returns BLOCKED with UNKNOWN_RECOVERY_REQUIRED;
the caller must inspect durable history rather than assume a transition succeeded.

Installation state never changes the execution emergency-stop ledger. Eventually,
production admission will require an active installation AND current execution
admission checks: ACTIVATED plus an emergency stop still blocks execution;
DEACTIVATED never admits production recognition. This slice does not wire a dormant
test activation into production writers or weaken their unconditional rejection.

## Storage, startup and audit boundary

The eventual production ledger belongs outside the recognition target in protected
installation storage. The local SQLite ledger is exclusively a disposable test
model, not a substitute for that infrastructure. Workspace creation allocates a new
temporary directory and cannot adopt a caller path. `workspace.install()` explicitly
creates a new dedicated ledger; assessment/state/startup cannot install it.

`activation_schema.install` is caller-transaction-owned and savepoint-protected.
It installs only `recognition_activation_installation` and
`recognition_activation_history`, immutable UPDATE/DELETE/REPLACE triggers and a
contiguous sequence trigger. It rejects extra objects rather than sharing an Explorer
or recognition target. SQLite FULL synchronous commits persist state across reopened
connections. A fresh process cannot adopt the disposable registry; production restart
and restore continuity remain external requirements.

Every accepted transition appends action, actor, prior/new state, full readiness
report, relevant generations, supplied UTC time, signed ceremony and previous hash.
Readers reverify hashes, signatures, action/state/installation bindings and monotonic
time. No passwords, TOTP secrets, private keys or arbitrary evidence text are stored.
Failed readiness checks are portable canonical reports; assessment does not mutate
the ledger or claim protected production audit retention.

No Flask/WSGI change, startup migration, target enrollment, authority provisioning,
database fallback, worker, scheduler, live recognition or production activation was
introduced. Slices 1–6 are unchanged in this slice.

## Validation

Focused tests cover every missing prerequisite, native failure states, expired
evidence/status, malformed generations, production/synthetic separation, missing
writer/recovery/stop contracts, explicit signed activation, durable deactivation and
suspension, concurrency/replay, stale/wrong-actor/wrong-action signatures, audit
immutability, explicit migration rollback, rejected target sharing, startup isolation,
boolean/environment/role/database bypass attempts and continued production rejection.
Independent expectations cover report/audit hashes, states, generations and actor.

Validation results:

- Focused activation: **28 passed, 66 subtests passed**.
- Activation plus trust/status/enrollment/execution/deployment regressions:
  **135 passed, 1 skipped, 193 subtests passed**.
- Full `tests/` pytest: **888 passed, 3 skipped, 966 subtests passed** in
  **217.01 seconds**.
- `git diff --check` and new-file whitespace checks: no whitespace diagnostics.

The regression/full launchers installed audit hooks rejecting socket connection/DNS
and SQLite access under the repository's `src/database` directory. Tests used fresh
disposable databases and ephemeral synthetic keys. On Windows the test commands ran
with approval outside the restricted filesystem sandbox so disposable temp-directory
creation/cleanup could work. An initial focused run exposed three unclosed test
connections during Windows cleanup; explicitly closing those fixtures resolved all
three failures. No dependencies were installed and no external service,
PythonAnywhere, production database, production key, trust root or authority was
accessed or created. No commit, push, deployment or production activation occurred.

Production activation must remain BLOCKED. These tests establish repository
contract behavior and disposable persistence, not protected production readiness,
cross-process/host fencing, real identity/MFA, restart/restore continuity or host
power-loss durability. Each external prerequisite above still requires independently
reviewed infrastructure and a production adapter; there is no approved production
provider to register in this implementation.

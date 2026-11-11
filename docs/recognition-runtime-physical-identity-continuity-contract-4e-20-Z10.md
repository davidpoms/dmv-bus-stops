# 4e-20-Z10: physical-identity continuity contract review

## Scope and authoritative question

This document evaluates the existing repository mechanisms for physical-identity
continuity throughout Z7's validated-observation consumption interval. It does
not implement a new mechanism, change filesystem assumptions or authorize fewer
checks. The 120-second ceiling and all earlier authority deadlines remain intact.

**What authoritative fact permits a consumer to trust previously validated
physical identity without rereading it for that entire interval? None is
established by the current runtime contracts.** Immutable stored observations,
SQLite reservations and trusted-operator maintenance instructions do not, by
themselves, supply that fact.

Sources inspected:

- [`authorization.py`](../src/review/recognition/authorization.py): `Target`,
  `target_identity`;
- [`administration.py`](../src/review/recognition/administration.py):
  `LocalAdministration`, `connect`, `observe_target`, restore-generation and
  filesystem-rebind ceremonies;
- [`runtime_validation.py`](../src/review/recognition/runtime_validation.py):
  `_physical`, `_identity_snapshot`, binding/profile/history validation;
- [`runtime_profile_schema.py`](../src/review/recognition/runtime_profile_schema.py)
  and [`runtime_operation_contract.py`](../src/review/recognition/runtime_operation_contract.py);
- [`runtime_attempt_schema_manifest_observation.py`](../src/review/recognition/runtime_attempt_schema_manifest_observation.py)
  and [`runtime_execution_coordinator.py`](../src/review/recognition/runtime_execution_coordinator.py);
- [`runtime_proposal_transaction.py`](../src/review/recognition/runtime_proposal_transaction.py)
  and [`runtime_activated_owner.py`](../src/review/recognition/runtime_activated_owner.py);
- [`enrollment.py`](../src/review/recognition/enrollment.py) and
  [`writer_boundary.py`](../src/review/recognition/writer_boundary.py), to distinguish
  existing synthetic witnesses and writer leases from physical-continuity authority;
- [Slice H](recognition-filesystem-rebind-slice-h.md),
  [Z6](recognition-runtime-final-validation-observation-continuity-contract-4e-20-Z6.md),
  [Z7](recognition-runtime-attempt-schema-manifest-observation-slice-4e-20-Z7.md),
  [Z8](recognition-runtime-z7-latency-diagnosis-slice-4e-20-Z8.md) and
  [Z9](recognition-runtime-schema-manifest-observation-consumption-contract-4e-20-Z9.md).

## Exact physical identity and related predicates

`authorization.Target` has exactly four fields:

| Field | Authoritative observation |
| --- | --- |
| `hostname` | `socket.gethostname()` in the observing process |
| `database` | `str(Path(database).resolve(strict=True))`, after requiring a file |
| `device` | The resolved path's `stat().st_dev` |
| `inode` | The resolved path's `stat().st_ino` |

For a native SQLite connection, `target_identity` obtains the main database path
from `PRAGMA database_list` before resolving and statting it. This is a path-based
observation, not a repository-defined descriptor-based inode pin. An open
connection's reported path is not independently certified to keep identifying
the same file throughout all later calls.

There is **no separate mount ID, mount generation, filesystem UUID, mount-namespace
ID, parent-directory identity or filesystem lease in this runtime Target**.
`st_dev` is an observed field that can reflect a mount/device change; it is not
an independently witnessed mount lifecycle. A mount event leaving every defined
observable unchanged is not distinguishable by this identity format. This review
does not invent an obligation or a new field to detect such an event.

The runtime profile stores `hostname`, `target_path`, `target_device`,
`target_inode`, `control_path`, `control_device`, `control_inode`, plus
`target_schema_sha256`. Device/inode values are canonical lossless decimal text
there. Actual Target values are strict integers and `_identity_snapshot` converts
them to decimal text for exact profile comparison. Hostname remains mandatory;
there is no hostname allowlist, optional-host rule or caller-supplied substitution.

`administration.observe_target` combines the four-field observation with a schema
SHA256. The fingerprint function is `enrollment._schema`: exact non-internal SQL
objects plus `application_id` and `user_version` under its existing isolation
checks. That digest is a **schema predicate**, not a mount/file-content incarnation
or proof that the physical identity cannot change. Its algorithm is unchanged.

Installation UUID, target UUID, owner, generation, binding/profile digests,
activation incarnation and auth/MFA epochs are additional logical scope
requirements. PID/thread, native connection, phase and reservation epochs are
owner requirements. They are not extra physical fields and cannot replace any
of the four Target fields. `connect` also checks existing absolute files and one
hard link at opening; link count is an opening precondition, not a persistent
physical-identity field or interval-wide guarantee.

The frozen operation target and physical snapshots retain their original exact
scope. Neither equal schema SQL nor an unchanged installation UUID makes an old
operation portable to a different observed physical identity.

## Current observation and consumption scope

`_persist_attempt` completes fresh `_evaluate` before Z7 `_mint`. `_mint` observes
both configured files, matches them to the authoritative subject and records one
opaque marker with immutable facts. I1/I2/I3 then insert only the expected inert
attempt, genesis and audit records on control.

At `_finish`, `_final_validation` calls `_write_proof`, which validates the
original owner/envelope, exact three-write graph and fresh control definitions,
manifest digest and isolation. Routing then exposes only the immutable schema
inventory through the original state's exact native/guarded control handles.
Every eligible `_objects` request calls `_check`; `_names` delegates to that path.
`_check` calls `_physical` on **both configured files** each time. The seven reader
sites identified in Z9 repeatedly reach that same observation.

The consumption interval is bounded by the original attempt phase's successful
entry proof and the loss of eligibility at finalization/commit or any earlier
invalidation. It is not an interval spanning issuance, another request, another
worker, metadata mode transition or target reservation reacquisition. Invalidation
before control commit and cleanup prevent reuse of the original marker afterward.

Live `_read_parts`/`_current` paths additionally use `_identity_snapshot`.
That kernel checks actual connection-path and configured-path observations,
matches the enrolled profile, verifies target schema and logical installation/
target/owner scope, and reads the auth epoch. `_subject_for_owner` observes target
and control while constructing the subject; `_finish_reserved` repeats current
scope/MFA, target query-only/change and time checks before manager-owned control
commit. Target remains reserved through that commit. These checks remain fresh.

## Component-by-component continuity analysis

In the table, “can change” means that the existing contract does not rule out an
external change on every supported host. It is not a claim that a particular OS
permits every replacement of an open file or that a hosted change was tested.

| Component | What establishes it / what can change it? | Can the change coexist with otherwise valid SQL reservations? | Current observation and invalidation | What continuity would need to establish |
| --- | --- | --- | --- | --- |
| Configured pathname | Frozen `LocalAdministration` Path inputs; new configuration/owner selects different inputs | Normal phase code does not change the frozen configuration; a new configuration is not the original scope | Original owner/scope checks and fresh path/profile comparisons reject mismatch; no cross-owner carry is allowed | Same exact configuration and original owner throughout the interval; this alone does not establish filesystem resolution continuity |
| Resolved pathname (`database`) | Strict resolution of the configured or SQLite-reported path; directory rename, symlink/junction retargeting or namespace mapping can change resolution | No repository namespace reservation is attached to BEGIN IMMEDIATE | The next strict observation may reject a changed/missing/non-file path or a profile mismatch; no external namespace-event epoch exists | The configured/reported paths continue to resolve to the same bound identity, or every relevant change causes authoritative invalidation before further consumption |
| Mount | No independent field; mount changes may affect resolution/device/inode | SQL transaction validity is not a mount-lifecycle witness | Effects on defined fields are detected at subsequent observations; mount events themselves have no runtime signal | An established guarantee covering effects on the existing fields; no invented mount identifier or assumption of hidden-event detection |
| Hostname | Actual `socket.gethostname()`; host administration/platform reconfiguration may change it | Same PID/thread/SQLite transaction is not a hostname immutability assertion | The next observation compares the actual hostname strictly; no host-change notification is wired to reservation epochs | An authoritative unchanged-host fact or comprehensive invalidation covering a hostname change |
| Device | Actual resolved file `st_dev`; device/mount/namespace remapping can change it | The code provides no implication that live reservations fix the reported value | The next strict observation detects a different value; no device-change event invalidates the marker at the event itself | Preserve the bound device observation or invalidate on any relevant change; no device-only tolerance |
| Inode | Actual resolved file `st_ino`; replacement or path retargeting can change the observed inode | An open handle and SQL reservation do not prove the configured path still names that handle's file on every supported host | The next strict observation detects a mismatch; there is no general file-replacement notification | Preserve the exact path-to-file relationship or invalidate before a stale observation is consumed; no “same path implies same inode” assumption |

An external mutation's boundary is the actual host/filesystem change, which may
occur between Python calls. The application's detection boundary is a later
strict observation. The repository does not currently equate those boundaries.
Path/device/inode identity also is not a content-version witness: unreported
metadata-identical in-place restores remain outside the trusted-administrator
protection claimed by `administration.py` and Slice H. No new anti-administrator
security model is introduced here.

## Evaluation of the four candidate models

### A. Immutable binding

Stored Target values and runtime-profile rows are immutable observations and
expectations. They are not authority proving that the actual filesystem/host
will remain unchanged. The frozen configuration fixes input values, not all
future resolution/stat results. The original open connections, BEGIN IMMEDIATE
and query-only mode constrain SQLite activity but do not establish the missing
namespace/host guarantee. **This model is not established for runtime physical
identity across the interval.**

### B. Repeated observation

This is the supported current model: point-in-time physical reobservation at
mint/entry proof, every eligible Z7 inventory consumption, and the existing live
identity/subject/final kernels. Cadence is **semantic-boundary/per-consumption**,
not a timer. The 16,151 count is the measured workload, not a new fixed-count rule.
No polling interval, TTL, every-Nth-call shortcut or once-per-request replacement
is defined. No current check is suppressed by this review.

The cadence preserves existing behavior by performing the same strict current
comparisons before each eligible schema-inventory use and retaining all final
checks. It supports decisions at those check points, not proof of uninterrupted
physical identity between them. Calling these checks “continuous” must not imply
an OS-level lock or perfect detection of every intervening change. **This model
supports current repeated validation, not reread-free whole-interval trust.**

### C. Explicit invalidation

The manager/authorizer/registry provide authoritative invalidation for application
events: extra DML (even zero-row DML), transaction/mode changes, poisoned/closed
contexts, reservation epochs and related scope mismatches. Cooperative database
changes serialize against the existing reservations.

Slice H's trusted-local rebind ceremony, where its own admission gates permit
it, requires exact expected generation, fresh preview, unchanged host/path/inode/
schema and only device drift. It appends a new generation and audit, revokes
authentication and invalidates pending approvals. Restore and enrollment are
separate ceremonies with their own gates. None is an automatic runtime repair or
a general notification service for host/filesystem changes.

Slice H explicitly requires operators to quiesce application/worker access and
filesystem replacement. It states that SQLite locks serialize database writers,
not trusted host replacement. That is an existing maintenance discipline, not a
machine-proven runtime lease covering every host/device/namespace event. It must
not be reinterpreted as permission to carry a live Z7 observation across rebind.

There is a related witness concept in `enrollment.py`, but it is explicitly
**synthetic/disposable only**. Its target includes parent path/device/inode,
`host_id`, `deployment_id`, `incarnation_id` and schema SHA, and its workspace
simulates reported storage replacement with an incarnation change. Its RLock
serializes workspace methods, not all OS filesystem operations. The module
explicitly disclaims production enrollment configuration and automatic detection
of unreported replacements. The current runtime profile/coordinator does not
consume that witness. Importing its pure `_schema` fingerprint does not import
the workspace's identity/witness model. It cannot be promoted to runtime authority
to fill this gap.

Writer-boundary “leases” likewise are narrow in-process mutation capabilities,
not filesystem-continuity leases. `verify_local` reobserves physical identity.
They supply no physical stability guarantee to Z7 and cannot be created here.

**Explicit invalidation is supported for the enumerated application events;
comprehensive physical-change invalidation is not established.**

### D. Scoped consumption

The exact original synchronous final-validation scope establishes owner,
connection, transaction, phase and reservation continuity subject to existing
checks. It does not establish physical continuity merely by having a short or
non-yielding call graph. No inspected runtime operation defines a smaller
multi-consumer interval in which the host/path observations are proven immutable.
A stat/resolution result is an observation, not authority for a later interval.
**No existing physical-continuity scope supports once-only Z7 consumption.**

## Repository-supported invalidation rules

| Event | Existing authoritative handling | Physical-continuity coverage/gap |
| --- | --- | --- |
| Connection replacement | Exact original native connections/registry checked by the owner and Z7 envelope | Old observation is ineligible; no transfer to a replacement |
| Reservation release | Original manager ends transactions and invalidates context/epochs | No observation crosses release or reacquisition |
| Reservation epoch change | Exact epoch comparisons; control epoch advanced before final commit; cleanup invalidates both | Reject old eligibility even if the connection object survives |
| Transaction/savepoint boundary | Existing authorizer permits manager lifecycle only; Z7 clears facts on transaction/savepoint activity | No continuation across a new transaction |
| Runtime-profile change | Original digest/scope and fresh durable profile/binding validation | No automatic adoption; an externally rewritten file is additionally a physical-identity problem |
| Generation change | Fresh binding/history/scope and exact expected generation | Prior generation's authority cannot survive; not an OS event detector |
| Activation change | Fresh independently verified incarnation/digest and pinned scope | Equal physical metadata does not preserve old activated authority |
| Target/control configured path change | New path cannot inherit original owner/scope; fresh observed path must match enrollment | No hidden rebinding; external resolution changes have no pre-consumption signal |
| Target/control file replacement | Subsequent actual path/stat/profile comparisons can detect changed fields | **Unresolved gap:** no general notification or established interval-wide exclusion of replacement |
| Mount/device change | Subsequent actual resolution/device/inode comparisons can detect changed fields | **Unresolved gap:** no runtime mount/device-change epoch; no independent mount field |
| Host identity change | Subsequent actual hostname comparison rejects mismatch | **Unresolved gap:** no host-change signal tied to original reservation eligibility |
| Extra DML, auth denial, code/schema mismatch, DDL/ATTACH, mode/scope change, expiry, exception or uncertainty | Original authorizer, envelope, expected-definition/manifest, live kernels and cleanup fail closed | These checks remain; none proves that all external physical events are observed |

A detected mismatch invalidates eligibility; it never silently refreshes pinned
values. An invalidated/expired/poisoned/spent owner is not revived by a later equal
stat result. Only an otherwise authorized fresh ceremony/owner can establish new
authority under its own contract; there is no automatic retry, rebind or adoption.

## Relation to Z6/Z7 and performance

Z6's M facts can have continuity across the exact three control inserts because
those inserts do not change the verified schema facts. That supported subset is
preserved. Physical identity does not automatically inherit M's continuity.
Current history/audit/FKs, claim graph, auth/expiry, profile/scope, activation,
approval/proposal/ACK, dependencies, emergency stop, readiness, physical/schema
kernels and authority deadlines remain fresh. `_subject_for_owner` and final
validation are not bypassed.

A Z7 observation **cannot currently become a reread-free, reusable validated
physical-identity observation for this entire interval**. Existing fields and
mechanisms do not supply the required authoritative unchanged-physical-state
fact or comprehensive event invalidation. No new token, lock, lease, witness,
OS guarantee or contract reinterpretation is specified to manufacture it.

Z8 measured 12.052 seconds in physical-observation work across 16,151 observation
validations. Successful, independently supported continuity could potentially
reduce repeated work, subject to a separately validated implementation. This
review does not claim that a contract will remove that cost, give a speedup
estimate or establish any improvement. No new measurements are made. Increasing
the 120-second ceiling is not an approved substitute.

## Validation and decision

This slice adds only this file. Validation is `git diff --check`; no pytest, Z,
T, broad suite, hosted/production access, deployment-key read, commit or push.
Production code, fingerprints, enrollment, observation cadence, filesystem and
authentication/authorization semantics are unchanged. No writer, target mutation,
execution, completion, recovery or activation is introduced.

The missing authority/mechanism is an established host/filesystem continuity
guarantee or complete trusted invalidation source for changes to the existing
physical fields throughout the proposed consumption interval. Current manager
signals cover application ownership and SQL lifecycle, not all relevant external
physical changes. Repeated physical-identity validation must therefore remain.
No once-only-consumption implementation boundary is approved by this review.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED

**OUTCOME B — continuity contract cannot currently be established**

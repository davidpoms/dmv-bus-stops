# 4e-20-Z9: schema/manifest observation consumption contract

## Decision and scope

**Outcome B: the existing contract does not establish that the complete validated
Z7 observation remains valid throughout final validation after one boundary
check.** Its immutable schema data and its current eligibility are different
predicates. Schema-data continuity is already authorized by Z6; operation-wide
physical-identity continuity without further observation is not established.

The precise missing contract is a physical-identity continuity/invalidation
contract covering the configured control and target paths, resolved paths,
hostname, device and inode for the entire proposed consumption interval. The
existing SQLite reservation/epoch contract does not provide that guarantee or
signal every external filesystem-identity change. A separate decision would be
needed to establish such continuity, or to define a predicate-equivalent
separation of connection-local schema facts from independently fresh physical
authorization checks. Neither alternative is invented or approved here.

This decision does not revoke Z6's supported reuse of static schema facts across
I1/I2/I3, declare all 16,151 checks a fundamental minimum, or authorize a longer
lifetime. Z7 remains functionally approved, Z8 remains performance-blocked, Z
remains BLOCKED and the authority ceiling remains 120 seconds. This slice creates
only this document; no Python, schema, migration, test or hosted state changes.

## Sources

The source of truth is:

- [Z6 continuity contract](recognition-runtime-final-validation-observation-continuity-contract-4e-20-Z6.md),
  particularly its common envelope E, M coverage and fresh physical checks;
- [Z7 implementation contract](recognition-runtime-attempt-schema-manifest-observation-slice-4e-20-Z7.md),
  which explicitly requires a recheck at every inventory use;
- [Z8 diagnosis](recognition-runtime-z7-latency-diagnosis-slice-4e-20-Z8.md);
- [`runtime_attempt_schema_manifest_observation.py`](../src/review/recognition/runtime_attempt_schema_manifest_observation.py),
  `_mint`, `_check`, `_write_proof`, `_final_validation`, `_objects`, `_names`;
- [`runtime_execution_coordinator.py`](../src/review/recognition/runtime_execution_coordinator.py),
  `_phase`, `_persist_attempt`, `_evaluate`, `_read_parts`, `_finish_reserved`,
  `_final_attempt` and `_State.authorize`;
- [`runtime_activation_authority_issuance.py`](../src/review/recognition/runtime_activation_authority_issuance.py),
  `_subject_for_owner` and `_current`;
- [`runtime_validation.py`](../src/review/recognition/runtime_validation.py),
  `_history` and `_identity_snapshot`;
- [`runtime_proposal_transaction.py`](../src/review/recognition/runtime_proposal_transaction.py),
  its owned connections, adapters, checks and authorizer;
- [`authorization.target_identity`](../src/review/recognition/authorization.py),
  together with `administration.observe_target` and the schema/manifest readers
  identified below.

No external documentation or hosted/production resources were accessed.

## Exact flow and creation provenance

The original manager's attempt phase reserves control with BEGIN IMMEDIATE,
then target with BEGIN IMMEDIATE/query-only. It registers one genuine admission
context with exact process/thread, connections, phase and reservation epochs.
It does not reuse the issuance phase's connections or reservation.

```text
_persist_attempt(original state)
  -> complete fresh _evaluate(state)
  -> schema_observation._mint(state)
  -> exact attempt INSERT I1
  -> exact attempt-history INSERT I2
  -> exact audit INSERT I3
  -> attempt_pending records the expected graph

_finish(state)
  -> schema_observation._final_validation(state)
       -> _write_proof(state)
            -> _check(state)
            -> exact new rows, audit suffix, protected baseline
            -> reread control definitions/isolation and verify manifest digest
       -> activate private routing for this original state
       -> _finish_reserved(state)
            -> _evaluate(state)
                 -> shared admission._collect(...)
                 -> issuer._subject_for_owner(state.context)
                 -> current attempt/authority/ceremony/scope/time validation
            -> _final_attempt(state)
            -> fresh _current(state), MFA, query-only/target-change/time checks
            -> invalidate reservation epoch; manager commits control
       -> clear routing and observation/facts
  -> original manager releases target and cleans up
```

Within `_subject_for_owner`, existing owner dispatch obtains the original
coordinator context. Session, approval, approved proposal/ACK, dependencies,
emergency stop, blocks, complete history, claim disposition and protected
readiness are freshly checked. It calls coordinator `_current`, builds the exact
subject, observes target/control again, and finishes with `_read_parts`/`_time`.
None of these decisions is supplied by the schema observation.

Coordinator `_read_parts` calls `_current` and compares its result with the
original scope and MFA epoch. `_current` delegates to the existing issuer kernel:
`_identity_snapshot`, latest binding, and independently verified current activation.
`_identity_snapshot` first reads pending-transition/history/control state and then
checks actual physical/schema observations, installation, target, owner and auth
epoch. Its nested `_history -> check_control` reads explain why schema inventory
consumers occur repeatedly even inside an eventual fresh identity check.

## Repeated object, callers and granularity

There is **one** `_Observation` marker and one frozen `_Facts` record on the
original attempt state. `_mint` creates them once. `_check` returns that same
`_Facts`; it does not reconstruct a trusted observation on every call.

Production callers of `_check` are exactly:

1. `_write_proof`, once at the final-consumption boundary;
2. `_objects`, on each eligible inventory retrieval. `_names` delegates to
   `_objects` for an eligible original owner/connection.

`administration_schema._control_objects` and `_control_names` provide the seven
direct schema-reader call sites:

| Reader | Requested value |
| --- | --- |
| `administration_schema.check_control` | Full control object/SQL inventory |
| `runtime_execution_claim_schema.manifest` | Inventory for normalized manifest projection/digest |
| `runtime_execution_attempt_schema.present` | Object names |
| `runtime_execution_attempt_schema.check_manifest_transition` | Object/SQL inventory |
| `runtime_activation_authority_schema.check_manifest_transition` | Object/SQL inventory |
| `runtime_enrollment_transition_schema.present` | Object names |
| `runtime_enrollment_transition_schema.historical_manifest` | Inventory for verified historical projections |

`_objects` returns the same immutable `facts.objects` tuple. `_names` constructs
a new tuple of names from it. Callers also construct dictionaries, normalized SQL
views and digest projections; those are derived data, not new trusted tokens.
Migration audit, predecessor and binding relationship checks still run through
their original readers. Z7 does not retain their complete validation results.

The measured **16,151** comprises one boundary `_check` plus **16,150** eligible
inventory retrievals. It is not a count of distinct observations, profiles,
claims, rows or operations. The original focused comparison also performs one
independent fresh manifest read outside activated observation routing.

The primitive's granularity is **per inventory request**, not per inventory row.
Multiplication comes from nested readers: history repeatedly invokes control
validation; control validation invokes claim/authority/attempt/transition row
validators; migration readers reconstruct installed and predecessor projections
and call other package readers. `claims.check_rows` performs migration-manifest
validation before its claim-row loop, so even zero claims do not eliminate that
work. Record and scope readers can invoke these kernels again. It would be
incorrect to explain the count simply as 16,151 claims or per-row checks.

## Immutable value versus current validated status

The object inventory, stored canonical representations, original physical values
and original normalized digest are immutable values. That does not freeze the
objects referenced by `_Facts` or the state they describe. Connections can end
transactions; owners can expire or be poisoned; epochs can advance; a configured
pathname can cease to identify the original file.

`_check` currently combines three kinds of proof:

- immutable-data/provenance binding: exact marker, original owner/phase, stored
  canonical scope/subject, authority, credential-scope digest and definition code;
- current owner/reservation validity: registry, PID/thread, active context,
  exact native connections, live transactions, epochs, write mode, mutation
  counters, denial/poison state and original deadlines;
- current filesystem identity: `_physical` calls strict `target_identity` on
  both configured paths and compares them with the stored physical observations.

`_write_proof` adds the exact post-insert graph/audit/baseline and fresh control
schema/manifest/isolation proof. Neither a prior `_check` nor a frozen `_Facts`
means all these predicates stay true for the rest of the call graph.

The original eligible consumers do share one process/thread, phase, exact
connections, transactions and reservations while checks succeed. Unknown
connections/adapters and standalone readers get fresh inventory reads. Issuance,
commit/cleanup, metadata ownership and reservation reacquisition are different
boundaries and cannot inherit eligibility.

## Mutation and invalidation boundaries

| Change | Existing boundary/detection | Consequence for once-only consumption |
| --- | --- | --- |
| Extra DML, including zero-row auth-denial DML | Coordinator authorizer clears observation/facts; existing authorization decision remains unchanged | A propagated validated value cannot ignore that revocation |
| Wrong I1/I2/I3 graph, extra/mismatched audit, protected mutation | `_write_proof`, `_check_attempt_graph`, `_final_attempt`, fresh row/FK/history validation | Exact-write proof is still mandatory; `total_changes+3` alone is insufficient |
| DDL/ATTACH or unowned mode/transaction/savepoint operation | Original authorizer denies/poisons; manager-owned lifecycle changes invalidate eligibility/epochs | No continuity across these events |
| Commit, rollback, cleanup, connection replacement or reservation reacquisition | Epoch/context/lifetime checks and manager cleanup | Original observation cannot cross or be revived afterward |
| Generation/profile/install/owner/auth/MFA/activation/approval/stop change | Fixed write permit excludes it; fresh authoritative kernels and envelope comparisons reject mismatches | No cached current authority follows from equal schema SQL |
| Expiry, clock anomaly, denial, exception or uncertain outcome | Existing owner/clock/finalization checks and cleanup | No usable result, renewal, automatic retry or adoption |
| Definition-code/schema-policy change | Z7 code-identity checks and fresh expected-definition validators | SQL reservation alone does not constitute a Python code-policy invalidation mechanism |
| External path/directory/symlink/junction/mount/hostname identity change permitted by the host | Subsequent strict physical observations detect mismatch; no SQL authorizer or reservation-epoch callback observes the external event itself | An entry-only physical check does not prove identity is unchanged at every later consumer |

**Physical identity is not established as immutable for the entire operation.**
The SQL reservation protects the reserved database transaction against competing
SQL writers under the supported locking contract. It is not a repository-defined
host/filesystem namespace reservation. No inspected owner installs a filesystem
identity fence or a corresponding external-mutation epoch. Holding an open
connection is not proof that the configured path and its directory/mount mapping
still identify that same file on every supported host.

The exact external mutation point is the host/filesystem event itself, potentially
between any two Python calls, not an authorized INSERT or a coordinator phase
transition. The current detection point is a later `target_identity` comparison
in `_check` or the live identity kernels. No single automatic invalidation
boundary for that event exists in the inspected code. Some hosts may restrict
particular replacements of open files; that does not establish the required
portable whole-operation identity guarantee. No hosted experiment is claimed.

Existing repeated checks are point-in-time observations, not a continuous
filesystem lock. This analysis does not claim that 16,151 checks eliminate every
possible filesystem race. Replacing them with one check requires an explicit
equivalence/freshness contract; merely noting that final `_current` still runs
does not supply that missing proof. Nor does a current SQL schema snapshot prove
unchanged hostname/path/device/inode.

## Consumption decision and missing contract

The proposed sequence is **not authorized as stated** under existing Z6/Z7:

```text
one complete observation validation
  -> immutable validated result
  -> no more observation-envelope/physical checks throughout final validation
```

Z7's consumers currently need schema data plus a currently eligible original
observation; they do not need a new execution/authentication credential. The
existing opaque marker has no separately approved operation-wide validated
status. Returning `_Facts` once or passing a Boolean checked flag cannot create
that status. No new token format, serialization, constructor or authority API is
specified here.

A future decision must establish either physical-identity continuity with a
complete invalidation rule for all relevant changes, or a reviewed separation
where immutable connection-local schema data is consumed independently of live
physical authorization. The latter needs exact validation points, rejection and
publication rules and a proof that intervening identity changes cannot make an
otherwise prohibited operation succeed. It cannot silently reinterpret Z6's
physical owner envelope as a timeless schema fact. Code-policy changes and all
existing authorizer/epoch/lifetime invalidations must also remain accounted for.
These are missing proof obligations, not mechanisms authorized by this document.

There is consequently no approved minimum implementation slice for once-only
consumption yet. Retain current behavior. Z6 invalidation remains fail-closed:
discard eligibility and perform required fresh authoritative validation through
an otherwise permitted original path. A later read does not revive a spent or
poisoned owner, extend its deadline or authorize re-enrollment/recovery/retry.

The present count is an API-granularity consequence of Z7's approved per-use
envelope, not a proof that 16,151 physical checks are intrinsically necessary in
every secure design. This Outcome B is deliberately narrower than claiming that
static schema facts cannot be reused at all.

## Performance estimate, not an achieved result

Reducing 16,151 observation validations to one would remove approximately the
measured **12.052s repeated physical-observation component**, subject to
implementation overhead and validation correctness. One boundary physical check
and every independently required live physical/schema check would remain. Some
of the additional 48,450 canonicalizations, 16,150 digest calls and code-identity
comparisons could also disappear only if their per-consumer necessity were
discharged by that future proof; none is removed here.

For scale, subtracting 12.052s from the instrumented enabled result of 35.339s
gives about 23.287s, before other implementation costs or savings. This arithmetic
is not a benchmark, an approved optimization, a PythonAnywhere prediction or a
guarantee that the complete G+2 metadata lifecycle fits 120 seconds. There is no
new performance measurement in Z9.

## Preserved security invariants and validation

Regardless of any future schema-data consumption decision, continue to freshly
validate authentication/expiry; approval/proposal/ACK; activation incarnation;
emergency stop; dependencies; current control state; complete current history and
audit head; current claim graph; readiness; authority expiry; and strict physical
identity/current target schema through existing authoritative kernels. Digest,
canonicalization, exact scope matching and global FK predicates remain required
unless their precise redundancy is separately proved. No observation substitutes
for `_subject_for_owner`, `_evaluate`, `_final_attempt` or final `_current`/time
checks. Control commits while the target reservation remains held.

Only `git diff --check` is run for this documentation slice. No pytest, Z, T,
broad suite, production access, hosted access, deployment-key read, commit or push.
No target DML, writer admission/capability, execution, completion, recovery,
readiness authority or activation is introduced.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED

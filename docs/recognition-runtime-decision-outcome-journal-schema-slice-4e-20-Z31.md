# 4e-20-Z31: inert decision-bound outcome journal schema and codecs

## Scope and assessment

Assessment **B: one new logical journal structure**, with separate control
decision/history and target witness placements. This refines
[Z30](recognition-runtime-decision-bound-outcome-journal-contract-4e-20-Z30.md).
Only deterministic DDL text, detached DATA codecs and read-only schema/row
inspection are implemented. No connection opener, installer, manifest registration,
migration, journal/witness producer, outcome resolver, authentication, admission,
writer or execution capability is supplied.

Implementation:
[`runtime_decision_outcome_journal_schema.py`](../src/review/recognition/runtime_decision_outcome_journal_schema.py).
Tests:
[`test_recognition_runtime_decision_outcome_journal_schema.py`](../tests/test_recognition_runtime_decision_outcome_journal_schema.py).

## Identity and exact detached codecs

Canonical decision identity is existing `authority_id` plus mandatory
`authority_sha256 = digest(authority body)`. No second journal UUID is introduced.
The journal does not change existing authority semantics or lifetime policy.

Every field below is immutable after creation. No codec accepts extra/missing
fields. All non-null fields are required, with `previous_sha256` the only nullable
event field. There are no mutable current-state or retry-authorized columns.

### Decision DATA

Format: `recognition-runtime-outcome-decision-v1`.

| Field | Type / nullable | Binding and purpose |
| --- | --- | --- |
| `format` | Exact string / NO | Version of detached decision data |
| `authority` | Existing exact canonical authority object / NO | Full existing authority codec validates exact operation/manifest/proposal reference, runtime scope/profile/generation/install/target/owner/auth/MFA, activation incarnation, approval, consent, physical observations/schema, dependencies/stop/readiness and deadlines |
| `recorded_at_utc` | Canonical UTC string / NO | At or after source issue and strictly before expiry; genesis uses exactly this time |

Embedding the complete source authority makes target witness DATA self-contained
for historical structural checks even if control inspection is unavailable. It
does not prove that authority was durably issued or that a caller is its owner.
No duplicate full profile, approval, proposal or credentials are added; the existing
authority has their exact bindings. Its source graph still requires independent
authoritative readers during any future live use.

### Control event DATA

Format: `recognition-runtime-outcome-event-v1`.

| Field | Type / nullable | Constraint and purpose |
| --- | --- | --- |
| `format` | Exact string / NO | Version |
| `authority_id` | Canonical lowercase UUID / NO | Exact source D |
| `authority_sha256` | Lowercase 64-hex SHA256 / NO | Digest of exact embedded source authority |
| `sequence` | Exact positive integer, not bool/float / NO | Contiguous genesis 1 through maximum 4 |
| `state` | Exact control enum / NO | Outcome state below |
| `at_utc` | Canonical UTC string / NO | Nondecreasing from decision and predecessor |
| `previous_sha256` | SHA256 or null / YES | Explicit null only at genesis; exact prior event digest thereafter |
| `actor_id` | Exact positive integer / NO | Equals original authority owner; resolver DATA never changes business actor |
| `evidence` | Exact state-specific object / NO | Decision, pending, uncertainty, no-commit or witness binding |

An outcome-only resolver must separately prove current owner authentication and
record audit provenance; `actor_id` is not a credential. Journal event digest is
the correlation anchor for the future control audit's exact subject. This inert
package neither appends general audit rows nor validates a producer's atomic
journal/audit transaction. Actual journal/audit linkage remains a future producer
integration requirement; do not infer it merely from a valid DATA row.

| State | Exact evidence fields |
| --- | --- |
| DECISION_CREATED | `decision_sha256` = digest of complete decision |
| TARGET_PENDING | `decision_sha256` = same exact decision digest |
| TARGET_UNCERTAIN | `pending_sha256`, `classification` |
| TARGET_FAILED | `pending_sha256`, `no_commit_evidence_sha256` |
| COMPLETED | `pending_sha256`, `witness_sha256` |

Uncertainty classification is exactly one of COMMIT_UNCONFIRMED, CONNECTION_FAILURE,
CLEANUP_FAILURE, INSPECTION_UNCONFIRMED, RESULT_PUBLICATION_FAILURE. A failure evidence
digest identifies required positive original-manager no-commit evidence; the codec
does not authenticate that evidence or let an inspector infer failure from absence.

### Target witness DATA

Format: `recognition-runtime-outcome-witness-v1`.

| Field | Type / nullable | Constraint and purpose |
| --- | --- | --- |
| `format` | Exact string / NO | Version |
| `decision` | Exact decision object / NO | Complete source D/scope |
| `pending` | Exact TARGET_PENDING event / NO | Exact D, sequence 2, predecessor/genesis, actor/time and decision digest |
| `recorded_at_utc` | Canonical UTC string / NO | At or after pending and strictly before source expiry; a precommit record time, not exact SQLite commit time |
| `outcome` | Exactly TARGET_COMMITTED / NO | Only supported target outcome fact |
| `effect_evidence_sha256` | Canonical SHA256 / NO | Binds complete separately verified business-effect/accounting evidence |

The witness codec reconstructs the unique exact genesis from the decision and
validates the full pending relationship. It is not satisfied by a supplied pending
digest alone. `effect_evidence_sha256` is an evidence reference, not an implemented
receipt codec or proof that business rows exist. **The actual target witness writer,
complete business-effect evidence verifier, and atomic coupling with business DML
remain UNRESOLVED integration mechanisms outside this inert slice.** No caller can
get execution permission by supplying a syntactically valid digest or witness.

## Exact SQL placements and fields

`definitions('control')` returns the first two tables and their guards.
`definitions('target')` returns the witness table and its guards. It returns text
only and does not execute it. Tests execute it only on SQLite `:memory:` databases.

Control decision table: `recognition_runtime_outcome_decisions`.
Target witness table: `recognition_runtime_outcome_witnesses`.
Both use these immutable NOT NULL fields:

| Column | SQL type | Constraint / purpose |
| --- | --- | --- |
| `authority_id` | TEXT | Canonical UUID, primary key |
| `authority_sha256` | TEXT | Canonical SHA256, unique |
| `installation_id`, `target_id`, `operation_id` | TEXT | Canonical UUIDs; exact authority projections |
| `operation_sha256`, `writer_manifest_sha256` | TEXT | Canonical SHA256s; exact source projections |
| `recorded_at` | INTEGER | UTC whole seconds, 0 through 253402300799; exact body time projection |
| `body_json` | TEXT | Non-null, valid JSON, no NUL, at most 1,000,000 UTF-8 bytes |
| `body_sha256` | TEXT | Canonical SHA256, unique; recomputed by row inspection |

Witness-only NOT NULL columns: `pending_sha256` and `effect_evidence_sha256`, both
canonical SHA256 and exact body/digest projections validated by row inspection.
The witness body is six fields; decision body is three fields. Binding triggers
check object/version, key count, stored projection identities, recorded time and
target outcome/effect reference as applicable. Cryptographic digest equality and
complete nested structure remain Python reader responsibilities, not fictitious
SQL hash functions.

Control history table: `recognition_runtime_outcome_history`:

| Column | SQL type / nullability | Constraint / purpose |
| --- | --- | --- |
| `authority_id` | TEXT / NOT NULL | Canonical UUID; FK to local decisions.authority_id |
| `authority_sha256` | TEXT / NOT NULL | Canonical SHA256; transition trigger requires same decision digest |
| `sequence` | INTEGER / NOT NULL | 1..4; composite primary key with authority_id |
| `state` | TEXT / NOT NULL | Exact control enum |
| `at` | INTEGER / NOT NULL | Bounded UTC seconds; body projection; no time rollback |
| `previous_sha256` | TEXT / nullable | Null or canonical SHA256; predecessor trigger enforces exact prior event |
| `body_json` | TEXT / NOT NULL | Same bounded JSON/NUL constraints; exact nine-field event decoded by reader |
| `body_sha256` | TEXT / NOT NULL | Canonical SHA256, unique; reader recomputes |

No new durable reservation, connection, PID, thread, epoch or lease is defined.
Actual reservation ownership remains process/thread/context/connection/transaction
bound and must be freshly proved by any future owner. The authority's physical
snapshot is historical identity DATA, never a reservation capability.

## State machine, uncertainty and crash representation

Exact control transitions:

```text
DECISION_CREATED -> TARGET_PENDING
TARGET_PENDING -> TARGET_UNCERTAIN | TARGET_FAILED | COMPLETED
TARGET_UNCERTAIN -> TARGET_FAILED | COMPLETED
TARGET_FAILED -> nothing
COMPLETED -> nothing
```

No repeated pending, uncertain-to-pending, new execution start, terminal rewrite,
CONTROL_COMMITTED enum or target outcome enum in the control table is allowed.
TARGET_COMMITTED exists only in target witness DATA. Durable control COMPLETED
is the correlated control outcome, not a redundant additional committed state.

Genesis must be exactly sequence 1 with explicit null predecessor and decision
record time. Start is sequence 2, within source authority lifetime. Later factual
uncertainty/failure/completion may be recorded after authority expiry; this does
not authorize further execution. Events remain time-monotonic and tied to D and
the unique pending event. COMPLETED requires an exact matching detached witness
and witness digest. Cross-store physical persistence is not proved by a detached
codec; a future factual resolver must observe/validate actual committed sources.

| Durable prefix | Meaning | Recovery/evidence | Retry / terminal |
| --- | --- | --- | --- |
| Decision plus genesis only | No recorded execution start; not positive proof of all real-world activity | Read-only historical inspection; original owner rules still apply | No capability/retry from DATA; non-terminal history |
| Pending without witness/outcome | Possible active/abandoned/uncertain execution | No absent-row inference; current authenticated factual inspection only | Retry prohibited; unresolved |
| Pending plus uncertainty | Explicit unresolved report | Only positive exact target proof or positive original no-commit evidence can resolve under a future authorized resolver | Retry prohibited; factual non-terminal |
| Target witness, missing control completion | Structurally correlatable target fact; actual commit/effects still need independent inspection | Same D/pending/effect proof must be positively validated | No re-execution; target fact immutable |
| TARGET_FAILED | Positive no-commit evidence reference, not a proof codec can authenticate | Historical only; no fence release | Terminal, retry prohibited |
| COMPLETED plus matching witness | Structural correlated outcome | Reader must separately establish source provenance/durability/effects | Terminal, retry prohibited |
| Partial/malformed graph, conflicting/wrong witness or unavailable source | UNKNOWN/integrity failure, not valid success | Fail closed; no repair/replay/adoption supplied | No retry |

A crash during either local transaction leaves a committed prefix or rolled-back
uncommitted rows. The schema does not claim cross-database atomicity. A crash after
target commit but before control recording is representable by target witness
plus pending/uncertain control history. A crash after completion before publication
is representable by terminal records, never a recreated process-local result.

## Uniqueness, append-only behavior and layered validation

Both decision/witness placements enforce unique authority ID, authority digest,
body digest, `(installation_id,target_id,operation_id)` and
`(installation_id,target_id,writer_manifest_sha256)`. Generation/profile/session
changes cannot open a new logical-operation/manifest slot in the same domain.
Control history enforces unique `(authority_id,sequence)` and event body digest.
Conditional contiguous transitions reject competing/duplicate starts and terminal
appends. Primary/unique indexes are SQLite's generated indexes; no extra speculative
lookup indexes are introduced.

Every table rejects UPDATE and DELETE, including no-op updates, and rejects INSERT
OR REPLACE collisions on every uniqueness identity even with recursive triggers
disabled. No deletion/expiry reuse, recovery authority, lease or fence-release
mechanism exists. Indefinite duplicate retention remains Z30 policy.

SQL guards handle local projections, FK/sequence/predecessor/time/state constraints.
They cannot validate remote committed data or compute canonical SHA256. Therefore
`check_schema()` and `inspect_rows()` are mandatory DATA-reader fences, not
optional authorization shortcuts. Exact package inspection rejects missing/changed
definitions, unexpected attached objects/triggers and attached databases.
Row inspection recomputes digests, parses complete canonical bodies, validates the
full history and projections, and checks FKs. Decision without genesis is a partial
graph and rejects. Control COMPLETED requires caller-supplied matching detached
witness DATA; no control-only read pretends to validate target completion.

No FK to a different SQLite database is invented. Existing attempt/ATTEMPT_CREATED
and general audit records are neither converted nor rewritten. Original authority,
proposal/ACK/approval and installed migration/audit provenance must be validated
by existing/future genuine readers; this inert module cannot establish that source
relationship by merely accepting a valid detached authority. SQL-only insertion
is not acceptance by the codec, current admission or proof of effects.

## Canonicalization and value rules

Use existing canonical serialization and `digest()`. Parsing rejects duplicate
JSON keys, extra/missing fields, noncanonical JSON/UUID/SHA/time, NULs, floats,
NaN/Infinity, unknown enums, inconsistent scope/predecessors and bools in integer
positions. Timestamps use canonical whole-second UTC and existing bounded integer
projection rules. Maximum journal body size is 1,000,000 bytes, also within the
existing bounded JSON parser; nested authority retains its own constraints.
Digests never include themselves. No secret/plaintext token material is added.

Existing authority physical device/inode integers are retained losslessly in JSON,
including values above signed SQLite integer range. They are not projected through
SQLite numeric casts or indexed as signed SQL integers here. Path/physical/scope
validation delegates to existing strict source codecs; no hostname exemption or
change to target_identity, transaction ownership, activation or Slice H occurs.

## Validation and next boundary

Focused tests cover deterministic/inert DDL, detached round trips, exact source
scope/time, malformed/NUL/float/bool values, canonical JSON, transition and terminal
denial, uncertainty/failure prefixes, source FK/projections, UPDATE/DELETE/REPLACE,
operation/manifest uniqueness, read-only inspection, partial schema/graph rejection,
tampered digests/projections and completion's explicit witness requirement.
All SQLite structures are in-memory. No real control or target file is opened.

The first test run exposed POSIX paths in borrowed detached test DATA on Windows;
only this test's synthetic paths were made platform-canonical without creating
those files. Production validation was retained. Final focused results are reported
with the task response; no broad tests, lifecycle runs or migrations are performed.

Next work, if separately approved, is security review of these exact inert
definitions and the still-unimplemented source-audit/business-effect evidence and
atomic witness integration obligations. No live migration, producer, resolver,
target mutation, writer/execution capability or performance claim follows from
valid inert schema. The current lifecycle remains blocked; the 120-second ceiling
is unchanged. No hosted/production resources or deployment keys were accessed.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED

WRITER CAPABILITY: BLOCKED

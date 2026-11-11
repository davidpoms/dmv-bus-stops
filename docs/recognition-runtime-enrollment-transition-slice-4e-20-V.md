# Slice 4e-20-V: inert enrollment-transition storage

Implements the control DATA/storage boundary from
[4e-20-U](recognition-runtime-enrollment-transition-contract-4e-20-U.md).
It does not implement a live plan-preparation producer, target DDL or an
enrollment-transition ceremony. No ordinary runtime request installs schema.

## Storage, codecs and guards

`runtime_enrollment_transition_schema` defines:

- Immutable `recognition_runtime_schema_transition_plans` and
  `recognition_runtime_schema_transition_history`, with the approved columns,
  source/destination binding/profile relationships and deferred audit FKs.
- Exact canonical plan/event formats, digest construction/parsing, bounded JSON,
  UUID/SHA/integer/UTC validation, NUL rejection and original nonrenewable deadline
  comparison. Detached objects are DATA, not credentials or reviewed DDL.
- Only PREPARED -> MIGRATION_INTENT -> SCHEMA_BOUND -> FINALIZED, with explicit
  predecessor digests, typed evidence, unique event/audit keys and audit linkage.
  UPDATE/DELETE and every REPLACE collision key are denied.
- A required UNIQUE binding-digest parent index for the approved digest FKs, with
  a corresponding BEFORE INSERT collision guard so OR REPLACE cannot use the new
  index to delete historical bindings. It is part of the recognized manifest.
- Current source profile/binding/owner/installation/target, nonactive activation
  head and MFA epoch guards. Event audits require unchanged pinned activation/
  MFA metadata and revoked proofs/sessions, absent step-ups, spent confirmations
  and no currently APPROVED approval history. Existing CREATED attempts block
  preparation; the inert installer still preserves their historical records.
- Plan-linked G+1 bindings, denied unlinked null-profile resets, and same-transaction
  G+2 profile/finalization linkage. Deferred destination/profile/audit FKs permit
  event-first insertion but prevent a half graph from committing. Existing
  profile/challenge/path/inode/schema guards remain in force; transition profiles
  additionally match the entire original runtime physical tuple.

G+1 has null profile and remains pending/non-executable. G+2 is structurally
finalized only with its complete exact binding/profile/challenge/enrollment-audit/
final-event graph. The old profile, approval bodies, authority/attempt records
and legacy execution records are not rewritten or promoted. Existing independent
runtime identity/authentication/activation checks still apply after finalization.

There is **no producer API** accepting a submitted plan/evidence as authorization.
Actual target auth-epoch/schema/physical observations, registered DDL-package
verification, local operator/private-log approval and cross-database transaction
ownership belong to the later typed transition ceremony. A coherent control
fixture alone cannot prove a target migration or make a runtime executable.

## Admission and inspection

Structural `check_control` accepts a complete valid pending graph as historical
DATA. `require_no_pending` denies every unfinished graph, including expired ones;
malformed graphs fail validation. The shared runtime physical-validation kernel,
administrative owner kernel and activated-readiness requirement invoke that
additional fence. Thus current runtime authentication/authority/coordinator paths,
administrative approval/execution and readiness/activation cannot use a pending
plan as authority. Initial 2c enrollment also rejects pending plans; this slice
does not add the separately scoped future enrollment wrapper.

Existing ordinary v3 administration remains blocked. No writer/legacy execution
format or lease is changed. No bypass flag, callback or public route is added.

`inspect_transition(absolute_control_path, plan_id=...)` opens control read-only
with query_only enabled and returns immutable historical data. It distinguishes
NO_PLAN, the four valid control prefixes, expired pending scope and malformed
storage. Every result denies execution/retry authority. MIGRATION_INTENT explicitly
reports uncertain target outcome. `target_commit_verified` is always false:
control-only inspection cannot distinguish H0 from an independently committed H1
or claim a coherent target/control snapshot. No target is opened by this reader.
Later paired inspection/DDL orchestration must supply that independent evidence;
there is no recovery/adoption/retry operation here.

## Explicit local installer

`migrate(config, expected_generation=..., operator=..., reason=...)` follows the
existing local migration pattern: control BEGIN IMMEDIATE, exact predecessor
schema/history checks, strict deployment control observation, query-only target
BEGIN IMMEDIATE, target verification and integrity/FK checks. Definitions plus
the installation audit are transactional. The installer verifies the resulting
exact manifest/empty extension and unchanged binding/target, commits control
before target release, and independently verifies committed control integrity.

Matching exact installation is a no-op after prerequisite validation. Partial or
incompatible schema, missing/altered migration audit, wrong expected generation,
identity mismatch or active state fails closed. No binding/generation/profile,
plan/history row, authentication or approval change is produced by installation.
The target schema/fingerprint and application rows remain unchanged.

The CLI action is `migrate-runtime-enrollment-transition-storage` in the existing
administration script. It requires the existing explicit target/control/key-file
paths, operator/reason and expected generation. Key-file configuration is retained;
this installer does not read the administrative key contents or create a key.
Only disposable/local test resources were used for validation.

The exact S2 -> S3 control manifest extension is registered and audited. Historical
claim/authority/attempt manifests exclude only the verified new definitions,
including the parent index and its collision guard. The target fingerprint
algorithm and initial-enrollment formats/semantics remain strict and unchanged.

## Failure semantics and validation

Precommit installer failure rolls back DDL/audit. A lost acknowledgement after
actual commit returns no success; independent inspection may find the complete
inert extension. It must not infer rollback or issue authority. Unknown/partial
states remain blocked. No SQLite retry/checkpoint workaround is introduced.

Focused tests use disposable synthetic control graphs only for constraint tests.
They cover canonical formats, malformed fields, immutability/REPLACE, migration
success/no-op/rollback/partial rejection/lost acknowledgement, scope and epoch
mismatches, legal pending prefixes, expired fences, actual admission denial,
concurrent preparation/finalization, G+1, atomic G+2/rollback, unlinked profile
reset rejection, inspection/restart and legacy/target isolation. The synthetic
H1 control fixture intentionally has an unchanged H0 target; real runtime
validation rejects it. It is not a provider that manufactures production authority.

Validation used the disposable-only database/network guard, `-B`, `-q` and
`-p no:cacheprovider`, with `-x` to isolate a first failure:

- Transition file: 14 passed / 44 subtests in the complete focused run; targeted
  follow-ups added the null-reset/collision and changed-epoch/head cases and
  rechecked affected admission/migration/finalization behavior. All **18 distinct
  transition tests** passed across these focused runs. Follow-up results were
  2 passed / 3 subtests, 2 passed / 2 subtests, 2 passed / 3 subtests, 3 passed,
  and 2 passed / 3 subtests. The last two runs checked complete 2c finalization
  provenance and populated pre-transition history preservation, respectively.
- Authority-schema file: aggregate run stopped with 23 passed / 93 subtests and
  one WAL process-interruption `disk I/O error` at the unchanged connection's
  synchronous PRAGMA. That exact WAL test passed alone (1 passed); only the
  remaining seven tests were then run (7 passed / 41 subtests). All 31 distinct
  authority-schema tests passed across runs; there was no clean aggregate rerun
  and no SQLite semantic/retry workaround.
- The initial focused FK failure exposed the missing UNIQUE binding-digest
  parent key. After adding the reviewed index/collision protection, the failed
  codec test passed alone (1 passed / 29 subtests), before subsequent focused runs.
- `git diff --check`, new-file whitespace and Python syntax checks passed.

No full suite, recognition/deployment family or unrelated execution tests ran.

Next boundary: **target-entry storage/migration**. Actual target DDL preparation,
transition orchestration and trusted transition enrollment remain separately
gated; inert control storage is not their implementation. Writer admission,
writer capabilities, family effects, seals, completion, recovery and activation
remain unimplemented by this slice.

No hosted/production resource access, real deployment-key reads, commit or push.

PRODUCTION AUTHORIZATION: BLOCKED
PRODUCTION EXECUTION: BLOCKED
PRODUCTION ACTIVATION: BLOCKED

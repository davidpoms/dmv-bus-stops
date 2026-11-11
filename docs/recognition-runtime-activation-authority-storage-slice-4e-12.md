# Slice 4e-12: inert activation-bound authority storage

This slice implements representation and an explicit local migration only.
There is no authority issuer, runtime owner registration, MFA ceremony, token
creation, claim consumption, writer capability, target mutation, completion,
recovery, readiness enablement or activation path.

The governing contracts are [4e-11](recognition-runtime-activation-bound-authority-contract-4e-11.md)
and its [4e-11-1 genesis clarification](recognition-runtime-activation-authorized-genesis-evidence-slice-4e-11-1.md).
No old operation, approval, 4d-1 claim or 4d-2 handoff is converted.

## Storage and codecs

`runtime_activation_authority_schema.py` defines exactly two new control tables:

- `recognition_runtime_execution_authorities`: the 21 approved columns, retaining
  the complete canonical authority scope in `body_json`. UUID/SHA/integer/UTC
  constraints, unique operation/manifest/confirmation/body/audit keys, historical
  binding/profile/activation/approval/confirmation FKs and deferred audit FK.
- `recognition_runtime_execution_lifecycle`: the 12 approved columns, but only
  sequence 1, state AUTHORIZED and kind AUTHORIZE are supported. Predecessor,
  target entry, seal and receipt fields must be null. No later-state enum,
  evidence codec or placeholder record is enabled.

Each table rejects UPDATE, DELETE and every INSERT OR REPLACE collision on its
primary/unique keys. Tests isolate each replacement guard from other rejecting
guards, avoiding false confidence from a simultaneous scope error. Security does
not depend on SQLite's ordering of different BEFORE triggers.

Insertion guards bind indexed values to the body, current installation/profile/
generation/owner/auth/MFA scope, exact activation head, v2 approval/history,
consumed authority confirmation, inactive current stop and absence of an operation
block or old 4d-1 claim. Physical device/inode comparisons use SQLite JSON `->`
text against canonical profile decimal text, never INTEGER/REAL casts. There is
no cross-database FK or claim of target-operation atomicity.

The authority and genesis must reference a **future** issuance audit sequence.
Its deferred FK and issuance audit trigger require matching genesis and audit;
an unrelated existing audit cannot satisfy the relationship. Historical readers
also validate the complete canonical authority/genesis/consent/audit graph,
ACK reference, activation ceremony/history and original authentication deadlines.
Expiry, revocation or generation changes do not rewrite or invalidate the
integrity of historical records; they do not make those records current authority.

Pure DATA APIs are `validate_authority`, `parse_authority`, `authority_digest`,
`validate_genesis_evidence`, `validate_genesis` and `parse_genesis`. Canonical
JSON/digest conventions are unchanged. They reject extra/missing/duplicate fields,
noncanonical JSON, malformed UUID/SHA/time/path, NUL, lossy physical values,
wrong integer types, scope inconsistency and lifetime violations.

Genesis evidence contains **exactly** `format`, `authority_id`,
`authority_sha256`; the format is
`recognition-runtime-authorized-genesis-evidence-v1`. Nothing is added to it.
The outer genesis and issuance audit must match the full authority digest,
operation, owner, reason and issue time. Later lifecycle events reject.

The 4e-11 lifetime remains at most 120 seconds, bounded by original primary,
session, step and confirmation expiry. Detached codecs enforce the canonical
bounds; stored-graph readers enforce the exact minimum of the referenced
deadlines. No renewal, caller-selected replacement scope or imported capability.

Parsing proves shape and content linkage, not fresh readiness, authentication,
target eligibility or permission to issue/write. Current target graph/dependency/
owner/physical validation and genuine future consent remain the future producer's
responsibility under reservations. No detached snapshot can replace them.

## Explicit migration and manifest transition

The only installer is
`migrate(config, *, expected_generation, operator, reason)`. There is no CLI,
web route, startup hook, provider callback or implicit runtime installation.
This follows the existing explicit claim-schema migration convention:

1. Validate absolute distinct configured paths and explicit canonical inputs.
2. Control BEGIN IMMEDIATE; exact existing schema, audit and expected generation;
   actual deployment control identity; existing profile history if enrolled.
   Require installed approval/activation/4d-1 storage and effective NOT_ACTIVATED.
3. Target BEGIN IMMEDIATE, then query-only. Use unchanged `administration._verify`
   for deployment target observations, schema and installation/target/owner IDs.
4. Separate read-only preflight snapshots verify both stores' integrity and FKs
   while both reservations remain held. No administrative key contents are read.
5. In one savepoint install the 13 exact new table/index/trigger definitions and
   append `runtime_activation_authority_schema_installed`. Its subject contains
   migration ID `recognition-runtime-activation-authority-storage-v1`, predecessor
   and installed schema digests, installation, generation and explicit reason.
6. Verify the exact full schema/manifest/graph and FKs, zero authority/genesis
   rows, unchanged binding/identity/target, query-only and fresh nondecreasing time.
7. Commit control while the target reservation remains held. Confirm control is
   committed and target still reserved. A fresh read-only control snapshot then
   verifies committed integrity and FKs before target release/rollback.

`PRAGMA integrity_check` can initialize TEMP. Running it on separate read-only
connections preserves the existing manager's isolated-main-connection rule;
that rule is not relaxed. There is zero target DML or target commit.

Already compatible storage is an unchanged no-op only after the same identity,
expected-generation, NOT_ACTIVATED and integrity prerequisites pass. Partial,
foreign or malformed definitions and missing/duplicate installation audits fail
closed. No file is repaired or silently upgraded. Generation/profile/binding,
authentication, approvals and activation history are not changed by installation.

Existing local migration tooling imposes no external backup-file/hash argument
for this control-only helper. Its actual required hashes are the exact schema
manifests and durable binding/audit digests, plus native integrity/FK preflight.
It neither creates nor verifies a hosted backup. The deployment policy still
requires deliberate verified backups and manual restore; this is not a backup
or schema/profile recovery ceremony.

### Preserving the old claim-install manifest

`administration_schema.check_control` recognizes the complete new extension or
its install audit; it never accepts a partial extension. The only changes to
`runtime_execution_claim_schema` are its historical manifest comparisons and
idempotent-reinstall comparison, delegated to the verified additive transition.
Claim formats, eligibility, enums, immutable rows and execution meanings are
unchanged.

`check_manifest_transition` proves that all new definitions match exactly, its
recorded installed hash equals the current schema, its predecessor equals the
current schema with **only those exact definitions** excluded, and that predecessor
equals the original immutable claim-install audit's installed manifest. The
claim reader reconstructs its original pre/post manifests from that verified
transition. Unknown objects, altered old definitions or modified old migration
audits reject; no old audit is rewritten or ignored. The new schema contains no
target tables and changes no enrolled target schema fingerprint.

## Failure, interruption and authority separation

Before control commit, failures roll back all new DDL and migration audit.
DELETE/WAL interruption fixtures terminate a disposable process before commit
or after confirmed helper completion and inspect ordinary SQLite durable state.
No checkpoint, journal deletion, retry or production workaround is introduced.

Commit acknowledgement, cleanup or post-commit integrity failure may leave the
whole extension durably installed. No success or capability is returned in an
unconfirmed case. Inspect the durable schema/audit/graph before taking another
explicit administrative action; never remove DDL, adopt execution or retry
automatically. Atomicity is control-local, not cross-database atomicity.

Synthetic test graphs intentionally exercise raw storage constraints and use
disposable installation/profile/physical observations, fake typed consent DATA
and explicitly synthetic readiness. They do not implement or invoke a real
authority producer/MFA ceremony, register a process-local attempt or provide a
production authority callback. Existing execution/writer paths reject their
plain dictionaries. Future production consumers must independently validate
fresh authoritative facts and genuine attempt ownership, never adopt fixture data.

Migration creates zero authority rows, zero execution claims and zero writer
capabilities. Ordinary v3 access remains `runtime_profile_contract_not_enabled`.
Legacy target claims/audit/receipts/seals, 4d-1 rows/history, 4d-2 handoffs and all
existing writer/readiness/activation semantics remain unchanged.

## Validation and next boundary

Focused tests cover canonical authority/genesis, exact evidence fields, malformed
and foreign scope, large lossless target/control physical values, immutable
collisions, deferred audit/genesis/FKs, manifests, protected-record preservation,
rollback, concurrent idempotence, uncertain commit and process interruption.
Guarded disposable-test validation completed:

- Authority storage/codecs + execution claims + claim consumption:
  **74 passed, 301 subtests passed**.
- Authority storage/codecs + claim disposition + activated owner + directly
  affected execution-claim schema/migration tests:
  **76 passed, 215 subtests passed**. This final group includes the additional
  canonical-scope/boolean-type regression tests.
- `git diff --check` and explicit new-file whitespace checks passed.

An earlier expanded focused run encountered one SQLite `disk I/O error` while
reopening the control file in the WAL process-interruption test. The unchanged
isolated test subsequently passed, as did both final groups. Its cause is not
established; no retry, checkpoint or journal workaround was added.

The requested `test_recognition_runtime_claims.py` does not exist; substitute
`test_recognition_runtime_execution_claims.py`. No recognition/deployment family
or full suite is run.

The next boundary is a separately reviewed **new authority-specific owner consent
ceremony**, not issuance or target execution. It must use genuine current runtime
owner/MFA and activation-bound scope and retain all 4e-11 checks. This slice has
no capability minting, authority issuance, target schema/profile transition,
later lifecycle codec, writer, recovery, readiness receipt or activation.

No hosted/production resource, production database or real deployment key is
accessed. No commit or push.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED

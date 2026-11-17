# Generation-5 pre-activation event foundation

This is one closed, explicitly authorized target-schema transition, not a schema
drift exemption or filesystem recovery. The package ID is
`recognition-preactivation-event-foundation-v1`.

## Closed runtime-prerequisite successor (v2)

The existing preview/completion backend and maintenance CLI also support the
closed package `recognition-preactivation-runtime-foundation-v2`. This is one
combined H0-to-H1 completion, not a separate prerequisite installer or an
intermediate schema edge. Preview simulates its additions before checking the
complete readiness inventory. Live schemas change only at signed completion.

V2 is selected only when all four source tables `recognition_operation_contracts`,
`recognition_operation_receipts`, `recognition_execution_claims`, and
`recognition_execution_seals` are absent. A partially present set is rejected.
Every event object must also be absent, as for v1. Its entire permitted manifest
is exactly the union of `event_schema.definitions()`,
`operation_schema.definitions()`, and `execution_schema.definitions()`. Any
already-present member must match the canonical SQL and existing related work
tables must be empty. Existing private schemas and every unrelated readiness
prerequisite must pass; this package cannot install or repair them.

The v2 plan has format `recognition-target-schema-completion-plan-v2` and adds
only `added_objects`, a sorted list of the exact missing canonical object names.
The definitions digest binds the full closed manifest, while the signed plan
binds the actual addition list and deterministic H1. DDL admission allows only
those additions; existing objects are never rewritten. Every added table must
remain empty. Existing data is checked before/after, excluding only the newly
created empty tables. Full execution-schema validation and removal of exactly
the signed additions must reproduce the immutable enrolled H0 fingerprint.
Runtime validation accepts H1 only through that verified lineage, never by
falling back to H0. Generation, binding, profile, MFA/authentication and activation
remain unchanged. V1 completed histories retain their original interpretation;
no completed installation is eligible for a second completion.

Browser preview selects the package from the strictly validated source. Signed
CLI preview requires the same existing inspection purpose with this explicit
subject (an old v1 inspection approval cannot inspect v2):

```json
{"kind":"target_event_foundation_preview","operator":"<operator>","reason":"<reason>","package":"recognition-preactivation-runtime-foundation-v2"}
```

Its approval uses `preview_binding(subject)`, which binds the v2 family and full
canonical manifest digest. Completion still uses the existing
`target_event_foundation_completion` purpose, exact signed plan, root, mandate,
owner/session proofs, signing domain and `migration_binding()` representation;
the migration family/definitions are those of the plan's closed package. The
offline signer accepts only these two pinned package policies. No new command,
signing ceremony, raw-token substitute, legacy transaction or force flag exists.
All existing DELETE/FULL, physical identity, pre-authority topology, empty work,
freshness, atomic commit and one-time consumption requirements apply to v2.

The remainder below documents the original v1 edge and shared ceremony. Where it
describes adding/projecting event objects only, v2 instead uses its signed exact
addition list. Do not run `install-contracts` against an enrolled v3 target.

## Contract

The original generation-5 v3 binding, runtime profile and enrollment audit retain
their exact bytes and enrolled target fingerprint **H0**. Completion adds exactly
`event_schema.definitions()` (three tables and nine immutable triggers) and records
the deterministic resulting fingerprint **H1**. It neither changes the raw target
fingerprint algorithm nor excludes event objects from that algorithm.

Before completion, ordinary runtime validation requires H0. After completion it
requires H1, the original H0 provenance, an intact signed completion audit and the
exact fixed event schema. Removing the fixed event objects must reconstruct H0.
There is no H0 fallback after completion. Additional, altered or missing schema
objects fail validation.

Hostname, absolute paths, device, inode, installation, target and verified owner
checks remain unchanged. A console filesystem-recovery authorization cannot
authorize this operation or worker admission. The maintenance request must run in
the already-enrolled physical runtime context. A console observing another device
number remains inadmissible.

## Source and preview

The source must have all of the following:

- Generation 5, a valid enrolled v3 profile, and both binding and activation ledger
  in `NOT_ACTIVATED`.
- Exact pre-authority control topology: administration, approvals, local readiness,
  runtime-profile and runtime execution-claim definitions. The execution-claim
  extension must already be installed with valid history.
- None of the fixed event package objects present; partial installation is rejected.
- Empty operation contracts, target execution claims/seals/receipts and control
  runtime execution claims/history. This edge does not carry pending work forward.
- Valid existing primary authentication, ENROLLED MFA and an administrative session
  bound to the existing profile. Completion does not consume another TOTP code.
- Valid integrity/foreign-key checks and existing DELETE journaling on both files.

Preview runs under the existing runtime owner's target/control writer reservations.
It backs up the target through an independent read-only connection into a private
temporary database, installs only the fixed definitions there, and invokes the
current complete execution-schema checker and readiness inventory. Every
substantive safety prerequisite must pass, including emergency-stop state.
The full twelve-check rehearsal is advisory; preview reports its absence/expiry.
Preview creates no rehearsal evidence. It rejects other missing schemas or safety prerequisites instead of offering a
partial completion.

Completion additionally requires focused deployment qualification and a verified
recoverable pre-change target/control backup pair. Existing exact signed-plan
approval and atomic H0/H1 lineage are unchanged. Qualify before obtaining the
final preview/signature: adding or changing qualification changes the plan's
readiness digest and requires a new preview and approval.

The plan binds H0/H1, fixed definitions digest, installation/target/owner/generation,
original binding/profile/enrollment digests, exact target/control physical
identities, exact control C0/C1 manifests, authentication/MFA epochs, owner-key hash,
existing target-data hash, readiness hash, source audit head, operator, reason,
creation and deadline. H1 is deterministic for the same source; the plan's time
window is bounded by existing credential expiry and `admin_auth.RECENT_SECONDS`.
Any change in a bound observation requires a new preview and approval.

## Protected interface and approval

For separately approved operator key setup and public-only root installation, use
the [minimal governance bootstrap runbook](recognition-governance-bootstrap.md).

The existing owner/CSRF-protected administration blueprint provides:

| Method and suffix under `/api/admin/recognition-control/` | Exact request JSON |
| --- | --- |
| POST `runtime-foundation/preview` | `{csrf_token, operator, reason}` |
| POST `runtime-foundation/complete` | `{csrf_token, serialized_approval, signature}` |
| GET `runtime-foundation/status` | No request body |

Responses inherit the blueprint's `no-store` policy and existing error handling.
There is no public signing endpoint, private signing key, caller SQL, package
selector, arbitrary hash override or browser activation action.

If browser preview returns `administrative_control_unavailable`, its private
`RECOGNITION_READINESS_DIAGNOSTIC` record now identifies a fixed stage and failure
class without exception text or request values. `configuration` and `owner_access`
precede authentication; existing history/runtime-identity stages still apply.
`foundation_prerequisites` covers source-plan checks, `foundation_copy` covers the
temporary target copy, `foundation_schema` checks the copy after installing the
fixed package, and `foundation_inventory` checks its remaining readiness requirements.
The record preserves the original HTTP response and never authorizes a retry or
relaxes a prerequisite. A generic 503 alone does not establish which check failed.
Browser preview does not load the governance root; signed completion does.

Approval reuses the existing independently installed production-governance public
root (`<control filename>.governance-root.json`), Ed25519 domain and canonical
`recognition-runtime-production-governance-v1` body. Its subject is exactly
`{kind: "target_event_foundation_completion", plan: <complete preview plan>}`.
The signed holder must identify the same owner, primary token hash and session
token hash as the authenticated request. Signed target/control identities and
binding digest must match the plan and current observations. Its sole approval is
the existing `Authorization` representation with `environment="production"`,
`migration_binding(PACKAGE, event_schema.definitions())`, the existing governance
mandate reference, exact target identity and signed expiry. No generic Authority
handle can be provisioned from this purpose.

## Signed maintenance CLI (no raw browser tokens)

`scripts/active/complete_recognition_foundation.py` exposes only `preview` and
`complete`. It calls the same `_plan`, fixed package installer, final validation,
atomic commit and immutable lineage as the browser backend. It does not activate,
create sessions, verify/consume a new TOTP, mint Authority handles, accept recovery
authorization or provide a legacy installation fallback.

This interface removes the need to possess or copy **raw browser tokens**. It does
not remove the existing MFA/session prerequisite: the external signer must bind
the hashes of still-valid primary and administrative records for the enrolled
owner/profile. Those records must already exist through the normal authentication
ceremony. Expired/revoked records, changed MFA epochs, missing profile links or
invalid signatures reject the command. There is no automatic choice of an actor
or session, and no issuance/reset of authentication. The existing
`admin_auth._session_hash()` trusted-approval continuation kernel checks the signed
references on read-only handles. Failed checks cannot persist denial reductions.

Both operations take a private, existing UTF-8 JSON envelope containing exactly
`{"serialized_approval": "<canonical signed body>", "signature": "<base64 signature>"}`.
The independently controlled signer uses the existing governance public root,
format, domain, mandate, physical identities, installation, binding digest, holder
and bounded issue/expiry fields. The CLI reads no private signing key and never
prints the envelope, raw tokens, seed/ciphertext or database rows.

For **preview**, the signed subject is exactly:

```json
{"kind":"target_event_foundation_preview","operator":"<operator>","reason":"<reason>"}
```

Its single `Authorization` has the existing production target/expiry fields and
`preview_binding(subject)`: family is the fixed package, permission `inspection`,
action `preview`, operation digest `digest(subject)`, policy digest
`digest(event_schema.definitions())`, null population and the existing governance
mandate reference. This new closed inspection purpose cannot authorize completion
or generic Authority provisioning.

For **complete**, supply the existing unchanged `target_event_foundation_completion`
approval described above, signing the *entire exact returned plan*, and the exact
`plan_sha256` separately. Signature verification and live credential/profile checks
are repeated under reservations. The CLI also asks the operator to type the same
digest. It does not accept a raw-token flag or an unsigned owner assertion.

The signed preview reserves both databases through the private attached owner,
enforces DELETE/FULL, marks the owner query-only and always rolls back. Only the
temporary clone receives event DDL. Output includes `read_only=true`,
`source_databases_modified=false`, generation, H0, H1, plan, plan digest, validated
preconditions and `execution_authority=false`. Local tests compare complete source
SQL/data snapshots before/after; an output flag alone is not independent proof.

Manual PythonAnywhere syntax, **only after every preflight below passes**:

```bash
# Set these variables to existing independently signed artifact paths and the
# reviewed preview digest. They are inputs, not files generated by this tool.
: "${PREVIEW_AUTHORIZATION_FILE:?Set the existing signed inspection envelope path}"
RECOGNITION_SQLITE_LIBRARY=/home/davidpoms/sqlite-runtime/3.54.1/lib/libsqlite3.so.0 \
python scripts/active/complete_recognition_foundation.py preview \
  --target /home/davidpoms/dmv_bus_stops.db \
  --control /home/davidpoms/recognition-admin-control.db \
  --key-file /home/davidpoms/recognition-admin.key \
  --expected-generation 5 --authorization "$PREVIEW_AUTHORIZATION_FILE"

: "${COMPLETION_AUTHORIZATION_FILE:?Set the existing signed exact-plan envelope path}"
: "${APPROVED_PLAN_SHA256:?Set the exact reviewed preview plan_sha256}"
RECOGNITION_SQLITE_LIBRARY=/home/davidpoms/sqlite-runtime/3.54.1/lib/libsqlite3.so.0 \
python scripts/active/complete_recognition_foundation.py complete \
  --target /home/davidpoms/dmv_bus_stops.db \
  --control /home/davidpoms/recognition-admin-control.db \
  --key-file /home/davidpoms/recognition-admin.key \
  --expected-generation 5 --authorization "$COMPLETION_AUTHORIZATION_FILE" \
  --approved-plan-sha256 "$APPROVED_PLAN_SHA256"
```

Run from the repository in the existing supported Python environment. Loader
execution precedes all sqlite3-dependent imports. A normal console with a different
hostname or NFS device from the enrolled profile **still fails**; this CLI does not
make that context admissible or extend deployment recovery into worker authority.

Successful completion returns `state="COMPLETED"`, generation 5, H1 as
`schema_sha256`, `production_state="NOT_ACTIVATED"`, `execution_authority=false`,
after post-commit lineage/identity validation. Nonzero completion exit reports an
unconfirmed outcome: inspect through the existing protected foundation status or
read-only `runtime_target_schema_completion.inspect()` before considering a new
preview. Do not blindly replay. A consumed authorization is never reusable.

The root must be a canonical, nonsymlink, single-link regular file; on POSIX neither
it nor its direct parent may be group/world writable. Existing trusted deployment
protection of ancestor directories, account and signing process remains required.
The root and historical authentication rows must remain available for subsequent
lineage verification. Expiry applies to consumption, not to the validity of a
properly consumed historical authorization. Later session revocation does not
erase history or revive the session.

## Atomic maintenance owner

Ordinary connections still require a single database and reject attachments. Only
the private synchronous maintenance owner attaches the configured target to the
file-backed control connection, with a fixed alias and `mode=rw`. Both databases
must already use **DELETE** rollback journals. The owner never switches journal
mode. WAL, memory and other modes are rejected. Both connections use FULL
synchronization; this is a connection setting, not a persistent mode change.

`BEGIN IMMEDIATE` reserves both databases. Separate isolated read-only connections
revalidate the complete source, authentication and exact signed plan while the
reservations are held. The private authorizer then restricts writes to fixed event
DDL, replacement of the single execution-claim schema-snapshot guard, and insertion
of the completion audit. Application-data DML, credential/MFA changes, unrelated
DDL and further attachments are denied. No attached handle is returned to callers.

Before one COMMIT the owner checks exact H1, unchanged pre-existing target data,
empty newly created event tables, exact control C1, foreign keys, signed lineage,
physical identities and remaining authorization lifetime. The immutable audit
action `runtime_target_event_foundation_completed` includes the complete plan,
plan digest, signed artifact, signature and `state="CONSUMED"`. This one event is
both schema lineage and one-time approval consumption; it is not an independently
committed authorization row. Failed transactions roll back target DDL, control
guard and consumption together. A lost commit acknowledgement requires inspection
of durable status, never a blind retry or automatic inverse migration.

SQLite multi-database atomic commit relies on rollback-journal/super-journal
semantics, correct VFS locking, durable file synchronization and filesystem support.
DELETE plus FULL is a necessary admission restriction, not independent proof that
a particular NFS/provider environment supplies these guarantees. Local subprocess
interruption tests cover before DDL, after DDL, before COMMIT and after COMMIT;
injected exceptions cover DDL, validation, audit and commit failures. They do not
simulate power loss or interruption inside the native SQLite COMMIT instruction.

## Downstream interpretation

The original claim installation audit remains at control manifest C0. Completion
adds a verified C0-to-C1 control-guard edge alongside H0-to-H1. Claim and authority
snapshot validators select H1 only for the exact completed profile. Their SQL scope
guards retain all existing predicates and select H1 through the typed completion
audit; authoritative readers additionally verify the complete signed lineage.
Historical manifest reconstruction preserves the original claim audit and orders
completion before any subsequent authority/control packages.

Generation, binding/profile rows, primary/admin sessions, MFA, authentication links,
approvals and activation records are unchanged by completion. Readiness can become
ready while activation remains `NOT_ACTIVATED` and execution authority remains
false. Activation and every later operation still require their existing ceremonies.
Existing v2 rebind, G+1 transitions and arbitrary installers are not modified or
implicitly authorized. This contract supplies no general migration authority for
later packages; their existing installation APIs remain separately gated.

## Eventual PythonAnywhere preflight

### Optional: recording genuine deployment-rehearsal observations

`local_readiness.record_deployment_rehearsal()` retains its legacy transaction and
audit format. Generation-5 v3 recording uses the existing runtime transaction,
strict enrolled identity/profile checks, target/control reservations and final
scope revalidation. Its v3 branch is pre-activation only. It appends only the
existing `local_deployment_rehearsal_recorded` record; it neither assesses
readiness nor invokes foundation completion, activation or recognition execution.
Evidence is copied and checked again before commit; pre-commit failure rolls back
the audit. A lost commit acknowledgement can leave a complete durable record;
inspect trusted durable state before retrying an unconfirmed outcome.

The evidence file/request is exactly a JSON object mapping all twelve
`local_readiness.REHEARSAL_CHECKS` names to lowercase 64-character SHA256 digests:
`sqlite_locking`, `concurrent_workers`, `filesystem_permissions`,
`control_persistence`, `backup_creation`, `backup_restoration`, `background_jobs`,
`restart_behavior`, `process_lifecycle`, `secret_protection`,
`no_startup_activation`, and `writer_lock`. No extra fields are accepted.
Each digest must identify actual preserved evidence from the approved disposable
host rehearsal documented in `recognition-deployment-rehearsal-slice-f.md`,
applicable to this installation/generation. Backup evidence must support the
unchanged declaration of daily backups, 30-day retention and a verified restore.
The recorder validates hashes and scope; it does not perform the rehearsal or
prove that submitted hashes came from genuine observations. Never supply hashes
of check names, placeholders, local/synthetic test outputs claimed as hosted evidence, or invented
observations. No source artifacts or credentials are printed or uploaded by it.

For the enrolled serving context, the existing owner/admin blueprint accepts
`POST /api/admin/recognition-control/runtime-activation/rehearsal` with exactly
`{csrf_token, generation: 5, operator, reason, evidence}`. Existing owner,
MFA/admin-session and CSRF checks apply; the session proofs are revalidated inside
the recorder transaction. No tokens are returned or copied to form fields.
On the already-authenticated Owner Activation page, the existing `call()` helper
can submit this action with the operator's real evidence map and adds CSRF itself:

```javascript
await call('runtime-activation/rehearsal', {
  generation: 5, operator: rehearsalOperator,
  reason: rehearsalReason, evidence: rehearsalEvidence
})
```

The three variables above are operator inputs, not generated evidence. The helper
uses the existing browser session; no raw primary/admin token is supplied.

Trusted-host tooling exposes the same recorder (no browser token or new signing
ceremony) through `manage_recognition_administration.py record-deployment-rehearsal`:

```bash
: "${REHEARSAL_EVIDENCE_FILE:?Set the absolute JSON evidence-map path}"
: "${REHEARSAL_OPERATOR:?Set the verified operator name}"
: "${REHEARSAL_REASON:?Set the factual reason identifying the actual rehearsal}"
RECOGNITION_SQLITE_LIBRARY=/home/davidpoms/sqlite-runtime/3.54.1/lib/libsqlite3.so.0 \
python scripts/active/manage_recognition_administration.py record-deployment-rehearsal \
  --target /home/davidpoms/dmv_bus_stops.db \
  --control /home/davidpoms/recognition-admin-control.db \
  --key-file /home/davidpoms/recognition-admin.key \
  --expected-generation 5 --evidence-file "$REHEARSAL_EVIDENCE_FILE" \
  --operator "$REHEARSAL_OPERATOR" --reason "$REHEARSAL_REASON"
```

The CLI file must be absolute, regular, non-symlink, single-link, bounded to 16 KiB
and distinct from the target/control/key files. Recording uses fresh time after
reservations and leaves the original audit target/binding representation intact.
A console with a different enrolled hostname/device/inode cannot use this CLI;
it must not bypass that refusal or reuse filesystem-recovery authorization.
Use the authenticated serving-context route instead. A successful action returns
`{"state":"RECORDED","generation":5,"evidence_checks":12,"execution_authority":false}`.
Then run the existing separate read-only preview/readiness action. Records must
match the current binding scope and be less than 86,400 seconds old, as before.

### Focused deployment qualification

No second PythonAnywhere account or persistent hosted rehearsal harness is needed
for the reduced contract. A qualification is a trusted operator observation, not
external attestation, a governance signature, activation or execution authority.
It is stored as `local_deployment_qualification_recorded` in the existing audit,
without adding tables or modifying binding/profile/authentication records.

Before recording it:

1. Review actual private DB/key files and parents, static-file mappings and logs;
   verify no secret exposure and that ordinary startup remains NOT_ACTIVATED.
2. Verify persistent target/control placement and observed persistence across the
   real deployment lifecycle. Preserve factual sanitized observations.
3. The recorder performs an actual independent-process DELETE/FULL locking/visibility
   probe on fresh disposable sibling files on each configured DB filesystem.
   It never performs probe writes against the target/control databases. The
   child must use the same SQLite version; a configured private loader is used
   before sqlite3 imports. Any timeout or unexpected writer admission rejects.
4. Create a coherent pre-change target/control backup pair using SQLite backup
   APIs, under a controlled/quiescent maintenance window. Do not copy open DBs
   with filesystem copy commands. Keep the pair in private storage. Recording
   compares both complete schemas and typed contents with the reserved live
   stores, reopens both copies, checks integrity/foreign keys, and records SHA256s.
   Concurrent changes cause rejection; do not relabel a stale pair as current.
   This verifies readable recovery copies, not a full hosted restart/restore drill.

The request contains `evidence` (exactly four real artifact SHA256s:
control_persistence, filesystem_permissions, secret_protection,
no_startup_activation) and `backups` with absolute `target` and
`control` backup paths. Never supply hashes of check names or synthetic tests as
observations of production. The actual file/locking/backup verification is not
replaced by operator assertions. Successful locking/concurrency/writer checks are
recorded by the actual probe, not supplied as additional operator hashes. The
active `sys.prefix` must contain a launchable Python interpreter with the same
SQLite runtime; unavailable child execution fails closed.
The bounded probe qualifies this client context; it is not provider attestation,
cross-host locking certification or proof against storage hardware failure.
Ordinary runtime physical identity checks remain unchanged. POSIX owner/mode
checks apply on production; Windows fixture runs do not certify production ACLs.

Use the existing authenticated Owner Activation page helper in the enrolled
serving context (no copying raw tokens):

```javascript
await call('runtime-activation/qualification', {
  generation: 5, operator: qualificationOperator, reason: qualificationReason,
  evidence: qualificationEvidence, backups: qualificationBackupPaths
})
```

Existing owner, recent primary, MFA/admin session and CSRF checks apply and the
session is revalidated under reservations. Inputs above are real operator inputs,
not generated examples. Success returns `state=RECORDED`, `generation=5`,
`execution_authority=false`. No source schema/data is changed.

The same trusted-host operation is exposed as:

```bash
python scripts/active/manage_recognition_administration.py record-deployment-qualification \
  --target /home/davidpoms/dmv_bus_stops.db \
  --control /home/davidpoms/recognition-admin-control.db \
  --key-file /home/davidpoms/recognition-admin.key \
  --expected-generation 5 --operator "$QUALIFICATION_OPERATOR" \
  --reason "$QUALIFICATION_REASON" --evidence-file "$QUALIFICATION_FILE"
```

Set the existing `RECOGNITION_SQLITE_LIBRARY` before running the CLI. The protected
input file is an exact JSON object `{evidence, backups}`. The CLI must itself run
in the enrolled physical context; a differently bound PA console cannot use it.
Use the authenticated serving-context route in that case.

Qualification binds the binding digest, generation/logical target, exact current
target/control physical identities, SQLite version and relevant implementation
digests. Changed scope requires new genuine observations and a fresh pair. It
has no arbitrary 24-hour rehearsal expiry. Backup files must remain unchanged,
private, single-link and without live journal/WAL artifacts. Missing, substituted
or modified copies block completion/activation. Before foundation mutation the
current target contents must still match the verified recovery point; otherwise
create a fresh pair and requalify. Completion repeats the locking check, and
rechecks qualification/permissions/backups before commit. Activation also repeats
the locking check before consuming confirmation and changing state.

After successful completion H0 remains immutable provenance and verified lineage
admits H1. Existing activation confirmation is still required. Full rehearsal
warnings may remain visible. Daily backup scheduling and retention remain an
operational policy, not twelve fresh prerequisites to every execution admission.
Any later restore must use the existing controlled restore/fencing procedure;
these backup paths are never permission to copy old stores over a live deployment.

### Completion preflight

The manual syntax above does not authorize skipping preflight. Before approving
deployment or consumption, establish all of the following in the real serving context:

1. Load private SQLite **3.54.1 before any sqlite3-dependent project imports** and
   verify the mapped library/capabilities. Local tests use SQLite 3.50.4 on Windows;
   they do not establish PythonAnywhere/NFS crash durability.
2. Inspect both journal modes read-only. Both must already be DELETE. Do not change
   mode as a side effect of this ceremony. An incompatible mode is a stop condition
   requiring a separate reviewed operational decision.
3. Rehearse the real loader/VFS/filesystem transaction and crash recovery using
   disposable copies only, including interruption/reopen of both attached files.
   Confirm filesystem locking, super-journal placement and durability guarantees.
4. Obtain a coherent target/control backup and a separately reviewed recovery plan;
   quiesce competing maintenance, filesystem replacement and schema writers. Do
   not restore only one database or manually delete committed completion metadata.
5. Confirm enrolled worker physical identities, exact source topology, empty work,
   genuine current readiness evidence and unchanged H0/profile provenance. Another
   console device number is not a substitute for worker identity.
6. Verify the independently provisioned governance public root and existing external
   signer custody; do not create a production trust root/key through this API.
7. Use the authenticated owner interface or signed maintenance CLI to preview, independently review the
   exact H0-to-H1 plan, obtain its narrowly scoped signed approval, and consume it
   before both plan and credential deadlines. Inspect durable status on uncertainty.

After a committed completion there is intentionally no automatic rollback command.
A paired restore is an independent controlled recovery procedure, not a way to
replay this approval. Unauthorized schema change, missing lineage, altered approval
or loss of the historical trust root fails closed.

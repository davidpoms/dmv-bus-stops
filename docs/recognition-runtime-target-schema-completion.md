# Generation-5 pre-activation event foundation

This is one closed, explicitly authorized target-schema transition, not a schema
drift exemption or filesystem recovery. The package ID is
`recognition-preactivation-event-foundation-v1`.

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
current complete execution-schema checker and readiness inventory. Every other
readiness prerequisite must already pass, including emergency-stop state and
current genuine deployment rehearsal evidence. Preview creates no rehearsal
evidence. It rejects other missing schemas or prerequisites instead of offering a
partial completion.

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

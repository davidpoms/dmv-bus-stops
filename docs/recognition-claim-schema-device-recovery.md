# Generation-5 deployment recovery: execution-claim schema only

This recovery is an explicit trusted-administrator authorization that accepts
unresolved storage-continuity uncertainty for this specific control-schema
migration. It does not establish physical continuity and does not protect against
a trusted administrator deliberately presenting a coherent clone.

## Scope and storage

The ordinary migration remains exact-identity only. Its explicit `recovery_sha256`
option accepts only an unconsumed `deployment_claim_schema_recovery_authorized`
event from the existing immutable administrative audit chain. No new tables,
binding versions, signing keys, MFA flows or runtime identity exceptions exist.

The event binds generation 5, installation/target/verified owner, operator/reason,
recorded and observed target/control identities, target/control schema digests,
current binding/profile digests, generation-4 enrollment-source binding digest,
enrollment audit digest, exact migration ID/definitions, NFS mount observation,
previous audit head, creation/expiry and the explicit uncertainty statement.
The current NFS source is corroboration, not historical proof or an allowlist of
PythonAnywhere private infrastructure. The mechanism requires Linux mountinfo.

Only device may differ. Hostname, canonical paths and inodes must match exactly;
both files must have the same current NFS mount observation. Live connection/path
identity, schema, logical scope, owner and enrollment provenance remain checked.
The authorization lifetime is 600 seconds. Any subsequent administrative audit
event before migration makes it stale. Run in a maintenance window: quiesce
application/worker access and filesystem replacement using existing deployment
procedures. SQLite reservations alone do not prevent host-level replacement.

The migration holds its existing control/target reservations. It retains integrity
and foreign-key preflight, query-only target, normal migration audit, final
identity/schema/provenance/mount revalidation and clock checks. Successful migration
adds a `deployment_claim_schema_recovery_consumed` audit event atomically. Failure
rolls back schema/migration/consumption; the authorization remains usable if still
fresh and the reviewed state remains exact. Successful recovery grants no future
operation permission; a second drift is not authorized. Ordinary deployment checks
can still reject device 59 afterward. Runtime readiness is evaluated normally and
may report further prerequisites; this is not a promise that activation is ready.

Generation, bindings, runtime profiles, enrollment history, MFA, authentication,
sessions, step-ups, approvals, target data/schema and activation are not rewritten.
The target's existing query-only reservation is not a target migration. Existing
v2 rebind and all runtime-worker identity/authority enforcement remain unchanged.

## Manual production ceremony after code review and deployment

These are instructions, not actions performed during development. Use the existing
trusted PythonAnywhere Bash console, application checkout and virtualenv. Preserve
the normal protected deployment configuration; do not put key contents in commands.
Arrange consistent backups using the existing backup procedure before maintenance.

```bash
export RECOGNITION_SQLITE_LIBRARY=/home/davidpoms/sqlite-runtime/3.54.1/lib/libsqlite3.so.0
read -r -p 'Target UUID from trusted generation-5 installation records: ' target_id
read -r -p 'Operator identity: ' operator
read -r -p 'Specific recovery reason: ' reason
scope=(
  --target /home/davidpoms/dmv_bus_stops.db
  --control /home/davidpoms/recognition-admin-control.db
  --key-file /home/davidpoms/recognition-admin.key
  --installation-id f5d48fcd-a8ce-45fb-ad5c-0009acaa7947
  --target-id "$target_id"
  --expected-generation 5 --owner-id 144
  --operation runtime_execution_claim_schema_installed
)
python scripts/active/recover_recognition_claim_schema.py preview "${scope[@]}"
```

Review the full snapshot: original devices 55, observed devices 59, expected
hostname/paths, target inode 224816447, control inode 224805688, logical IDs,
schema/binding/profile digests, and current NFS source/mount. Stop on any unexpected
value. The code is not hardcoded to these reported physical values: explicit
digest approval binds the actual reviewed observation. Preview performs no writes.

```bash
read -r -p 'Reviewed snapshot_sha256: ' snapshot_sha256
python scripts/active/recover_recognition_claim_schema.py authorize "${scope[@]}" \
  --operator "$operator" --reason "$reason" \
  --approved-snapshot-sha256 "$snapshot_sha256" \
  --accept-storage-continuity-uncertainty
```

Type the same full snapshot digest at the confirmation prompt. Authorization prints
the uncertainty statement, then JSON with `recovery_sha256` and `expires_at` (Unix
seconds). Neither value is invented or fixed in this document. Within 600 seconds:

```bash
read -r -p 'Returned recovery_sha256: ' recovery_sha256
python scripts/active/recover_recognition_claim_schema.py migrate "${scope[@]}" \
  --operator "$operator" --reason "$reason" --recovery-sha256 "$recovery_sha256"
python scripts/active/recover_recognition_claim_schema.py status "${scope[@]}" \
  --recovery-sha256 "$recovery_sha256"
```

Expected migration JSON:

```json
{"generation":5,"installed":true,"migration_id":"recognition-runtime-execution-claims-v1"}
```

Status must report `state=CONSUMED`, `installed=true`, `generation=5`, the unchanged
profile digest, `activation_state=NOT_ACTIVATED`, and `execution_authority=false`.
Status validates durable history/schema but grants no permission and does not
require console identity to equal the old deployment identity. Resume only the
existing owner readiness inspection; do not infer activation or execution authority.

## Failure, expiry and rollback

If a response is lost, use `status` first, never blindly repeat migration. If it
shows CONSUMED/installed, the transaction committed. A replay fails explicitly.
If AUTHORIZED/not installed, the transaction did not install the extension; inspect
the failure and freshness before any retry. If status itself fails, stop for trusted
state inspection. An expired/stale authorization needs a new preview and approval;
old immutable audit events stay in place.

There is no post-commit database down-migration. Do not delete tables/audit events,
rewrite the binding or restore just one database. After a committed migration,
keep capture disabled and NOT_ACTIVATED while diagnosing. Reverting application
code does not undo schema installation; retain code that recognizes the extension.
Any database restore requires the existing controlled recovery procedure and a
separate policy decision. Failed migration needs no manual schema cleanup because
DDL and consumption roll back atomically.

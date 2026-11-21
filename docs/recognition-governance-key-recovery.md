# Restricted offline governance-key recovery

This is a new, explicit single-owner recovery policy. It is not a permission
implied by G13, ordinary ownership, MFA success, a typed fingerprint or a new
governance key. It performs no runtime enrollment, identity recovery, activation,
schema migration or execution. The original installed governance root is NEVER
replaced. The initial `recognition_governance.py install-public-root` is unchanged.

## Trust and scope

The already authorized deployment custodian must approve deployment of this
policy and authenticate to the host using the existing operator account. Only
the local tool runs recovery: there is no HTTP endpoint and Flask request
contexts are rejected. The tool checks canonical, protected, single-link files
and ownership. It does not claim those checks prove that the project owner
approved a request, or that Python can attest a PythonAnywhere console login.

One-time enrollment additionally requires BOTH a fresh, purpose-bound challenge
delivered by the configured real email transport to the installation owner's
already verified address AND a fresh TOTP from the existing ENROLLED credential.
The complete installation/owner/key/source-scope/audit-boundary request is in the
email and must match the custodian's reviewed request digest. Caller-supplied
email addresses, browser sessions, ordinary login links, Root B signatures and
development email outboxes cannot substitute. The same person may be owner and
custodian; this does not give normal application administrators recovery power.

**Trust assumption:** control of that verified mailbox and enrolled authenticator,
acting through the authorized host custodian, is explicitly delegated recovery-key
enrollment authority. This is independent of the inaccessible governance key.
Full deployment-account/host compromise is outside the existing boundary: a
process with the same UID can read host secrets and alter code. File modes cannot
isolate it. This is not provider attestation or an external rollback witness.

The maintenance owner validates canonical v3 binding/profile/enrollment and
schema lineage, installation/target/owner, schemas, current paths and inodes,
current physical observations, protected MFA key, administrative clock and
DELETE/FULL settings. It never calls runtime `_identity_snapshot()` or creates
runtime credentials. Console hostname/device may differ from the runtime profile;
those exact console observations are bound to this maintenance operation ONLY.
The strict runtime comparison and closed G5/57,57 -> G6/49,49 contract are unchanged.

This initial implementation is deliberately restricted to `NOT_ACTIVATED` with
empty operation-contract/decision/execution/claim/block/seal/receipt history,
no acknowledged proposals, no issuer history, no pending
enrollment transition and no unfinished successor. It supports repeated root
cutovers using the same recovery key in this inactive, no-work state. It does
NOT implement post-activation or unsettled-work key recovery. In particular,
expired successor preparation is not silently canceled. Resolve such a state
under its existing contract before attempting recovery.

## Storage, ordering and interruption

No new SQLite schema is installed. Existing immutable `recognition_admin_audit`
stores these closed actions:

* `governance_recovery_enrollment_requested`: full public request and SHA256 of
  its random email token. Neither email token nor TOTP nor seed is recorded.
* `governance_recovery_key_enrolled`: full public certificate and its digest,
  linking the request and attesting the custodian/email/TOTP verification.
* `governance_root_recovery_committed`: exact recovery-signed cutover plan,
  certificate and digest. The approved audit predecessor must still be the head.

The certificates are canonical JSON at:

```
<control>.governance-recovery/enrollment.json
<control>.governance-recovery/cutover-00000001.json
<control>.governance-recovery/cutover-00000002.json
```

The certificate set must exactly match the committed audit lineage. Files are
regular, non-symlink, single-link and protected, as is their directory. The
recovery private key never enters this directory or the host.

Each owner reserves CONTROL before TARGET. TARGET remains query-only. A fixed
SQL authorizer permits only audit inserts and the existing MFA counter/throttle
changes; no credential issuance, revocation, schema change or target write is
permitted. The existing TOTP denial commits its throttle/denial audit only: no
recovery event has been staged at that point. Successful enrollment consumes the
counter and records enrollment in the same CONTROL commit. Invalid TOTP makes
the exact-head request stale; it is not automatically retried. Wait for expiry
and review a fresh request. The existing 5-failures/15-minute throttle still
applies, including failures from ordinary MFA authentication.

Enrollment and cutover use the existing paired UTC/monotonic guard from operation
entry through the final pre-commit check. Backward or stalled UTC anomalies and
expiry during processing reject and roll back. The monotonic budget is clipped
to the approval's original remaining lifetime, including reservation acquisition;
verification never starts another 600-second allowance.

Commit the event first, retaining target reservation through confirmed commit.
Only after connection cleanup exclusively publish the complete public certificate
and fsync using the existing publication helper. Never overwrite an existing
file. SQLite and filesystem publication are NOT one atomic transaction.

If commit/publication acknowledgement is uncertain, STOP and use `inspect`.
`PUBLICATION_PENDING` denies all governance key selection, including historical
verification, and never falls back to A. `publish-committed --id <exact-id>` can
publish only the one missing certificate derived from committed data, without
another audit event or credential consumption. Expiry after committed enrollment
or cutover does not prevent fulfilling that exact publication. Missing history,
conflicting/modified files, duplicates and extra certificate files are errors;
the tool does not repair them. Preserve the DB, original root and complete
certificate directory together in backups. A coherent rollback of all of these
is not detectable without an external witness, which this contract does not add.
Publication completion also reserves the target and requires the committed event
to remain the audit head, with unchanged schemas and physical observations. Any
intervening audit write or changed scope requires explicit further review; there
is no automatic reconciliation or newly issued approval.

## Current authorization versus historical verification

Current approvals use the last fully committed AND published root only. Retired
keys cannot authorize new actions, even with backdated timestamps. The recovery
key signs a separate domain and the exact `recognition-governance-root-cutover-v1`
plan only; it cannot sign ordinary governance approvals or replace itself.

Historical readers require actual membership of the complete event in the
validated audit chain. The installed original root selects events before the
first cutover; each later root selects events after its authenticated cutover
sequence and before the next one. Caller timestamps and key IDs never select a
root. Existing approval-purpose, holder, expiry, MFA, profile and physical checks
are retained. Preserving an old public key does not revive a spent or expired
live approval. Foundation and G5/G6 histories use their existing historical-time
checks; finalization retains its existing live expiry checks.

## Offline preparation (only after approval; not run by deployment)

Use an interactive operator terminal and a protected directory OUTSIDE every
repository. The following paths are proposed new artifacts, not existing keys:

```powershell
$govDir = "$env:USERPROFILE\.dmv-governance"
.\.venv\Scripts\python.exe -B scripts/operator/recognition_governance_recovery.py keygen `
  --private-key "$govDir\recovery-private.pem" `
  --public-key "$govDir\recovery-public.json" `
  --installation-id f5d48fcd-a8ce-45fb-ad5c-0009acaa7947 --owner-id 144 --confirm-offline
```

Private output is encrypted PKCS#8 PEM with a non-echoed passphrase and no
overwrite. Preserve two protected offline backups and independently recoverable
unlocking material; do not keep all copies behind one forgotten passphrase.
Test backup usability before enrolling. Transfer ONLY `recovery-public.json`.
Losing both the recovery credential/backups and its unlocking material is NOT
automatically recoverable; there is deliberately no self-enrollment/reset escape.
Generate any replacement ordinary governance key using the existing approved
offline bootstrap; transfer its public JSON only. Never upload either private key.

## Host procedure (manual, after review; no operations run by this document)

Use the supported Python/SQLite environment, actual repository and existing email
transport configuration. No SMTP secrets or tokens belong in command arguments.
All workers/tools must first run the new verifier; mixed old/new verifiers would
disagree about the active root. Do not start any other governance ceremony during
these reservations. None of the commands activates recognition.

```bash
cd /home/davidpoms/dmv-bus-stops
export RECOGNITION_SQLITE_LIBRARY=/home/davidpoms/sqlite-runtime/3.54.1/lib/libsqlite3.so.0
RECOVERY=(python -B scripts/operator/recognition_governance_recovery.py)
SCOPE=(--target /home/davidpoms/dmv_bus_stops.db
       --control /home/davidpoms/recognition-admin-control.db
       --key-file /home/davidpoms/recognition-admin.key
       --installation-id f5d48fcd-a8ce-45fb-ad5c-0009acaa7947 --owner-id 144
       --original-public-key-sha256 7528f333c6f1fd54aaee1f35d8f150ce199ca1e674f40479be536b9594d6ce90)
"${RECOVERY[@]}" request-enrollment "${SCOPE[@]}" \
  --recovery-public-key /home/davidpoms/recovery-public.json \
  --reason 'Enroll independent offline recovery credential' \
  --output /home/davidpoms/recovery-enrollment-request.json
```

Compare the complete mailed request, public-key fingerprint, source hashes and
request digest. Within 600 seconds, use the actual returned values:

```bash
"${RECOVERY[@]}" enroll "${SCOPE[@]}" \
  --request-id <returned-request-id> --approved-request-sha256 <reviewed-request-sha256>
```

The digest confirmation, email challenge and fresh TOTP are prompted; secrets
are non-echoed. Success is `READY` with the enrolled recovery-key digest. A
failed/uncertain email send leaves a request without authority; inspect and let
it expire before requesting another. Do not blindly rerun a failed enrollment.

Then plan the exact cutover (this operation changes no database contents):

```bash
"${RECOVERY[@]}" plan "${SCOPE[@]}" \
  --new-public-root /home/davidpoms/replacement-root.public.json \
  --reason 'Replace inaccessible ordinary signing credential' \
  --output /home/davidpoms/governance-cutover-plan.json
```

Transfer that public plan offline. Review it, sign with the RECOVERY key, then
transfer only the resulting public envelope:

```powershell
.\.venv\Scripts\python.exe -B scripts/operator/recognition_governance_recovery.py sign-cutover `
  --private-key "$govDir\recovery-private.pem" --public-key "$govDir\recovery-public.json" `
  --plan "$govDir\governance-cutover-plan.json" --output "$govDir\governance-cutover-envelope.json"
```

Signing and commit must both occur within the plan's 600-second lifetime and
without intervening audit writes. If that timing is missed, discard the unused
plan and review a fresh plan. Never edit timestamps.

```bash
"${RECOVERY[@]}" cutover "${SCOPE[@]}" \
  --authorization /home/davidpoms/governance-cutover-envelope.json \
  --approved-plan-sha256 <reviewed-plan-sha256>
"${RECOVERY[@]}" inspect "${SCOPE[@]}"
```

`READY` plus the expected current public-key fingerprint proves the matching
commit/publication pair. Root A remains byte-for-byte unchanged. Generation,
binding/profile, ordinary primary/session/authentication records, MFA enrollment,
activation and target data remain unchanged. Enrollment alone advances the MFA
last-counter; use a NEW code for subsequent authentication. Old process-local
governance registrations fail their existing root-digest recheck.

For `PUBLICATION_PENDING` only, after inspecting the exact committed ID:

```bash
"${RECOVERY[@]}" publish-committed "${SCOPE[@]}" --id <exact-pending-id>
```

This procedure does not fix device 57 -> 49. After current-key verification,
resume the existing fresh G5->G6 successor ceremony, then focused qualification,
foundation/readiness and separate explicit activation. Never reuse stale signed
plans, consumed challenges or qualification from another implementation/scope.

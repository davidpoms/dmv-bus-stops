# Slice H — Trusted-host filesystem identity rebind

## PythonAnywhere device-number drift

The reported deployment preserved the same hostname, absolute target/control
paths and file inodes, but the filesystem device number (`st_dev`) changed from
52 to 55. Ordinary administrative verification correctly compares the entire
stored identity and rejects this as `control_identity_mismatch`. This report is
the operator-provided scenario; no PythonAnywhere account or operational database
was accessed to verify or repair it during implementation.

H adds a narrow, explicit trusted-host ceremony for this case. It does **not**
change `target_identity()`, remove device numbers from authorization, introduce
runtime tolerance, or add a web route/configuration bypass. After rebind, normal
verification requires exact equality with the newly pinned device numbers.

## Preconditions and effects

`administration.rebind_filesystem_identity` requires:

- Existing compatible control storage, a valid binding chain and audit chain.
- Explicit nonempty operator and reason, the exact expected integer generation,
  and the SHA256 returned by a fresh existing target preview.
- Configured target/control absolute paths exactly matching the bound canonical
  paths; observed hostname, path and inode unchanged for each file.
- Exact identity field sets; only `device` may differ. Either or both files may
  have device-number drift. At least one must differ: a no-op is rejected.
- Current preview digest matching under locks, target schema fingerprint matching
  the pinned schema, valid existing installation schema, unchanged installation
  UUID, target UUID and owner ID, and the pinned owner still verified with role
  `owner`. No schema installation, migration or UUID replacement is performed.

The ceremony acquires control then target `BEGIN IMMEDIATE`, following the existing
lock order. It updates only the control store: appends generation N+1 with current
physical observations, the previous binding hash and `production_state=NOT_ACTIVATED`;
revokes primary proofs and administrative sessions; deletes step-ups; marks
confirmations used; and invalidates effective pending approvals using the existing
approval history mechanism. It appends `filesystem_identity_rebound` with operator,
reason, old/new generation, preview digest and old/new target/control observations.
It reobserves both identities before commit and fails closed on another change.

All those effects share one control-store transaction. The target writer
reservation remains held through that commit; the target has no data/schema
writes and is not committed. An audit/validation failure rolls back the entire
control update. Concurrent callers with the same expected generation cannot both
succeed; the second receives `filesystem_rebind_generation_conflict`.

The generation change makes prior activation and deployment rehearsal evidence
inapplicable through the existing A–G contracts. Production remains effectively
NOT_ACTIVATED; old approvals do not become executable. MFA enrollment/key material,
target UUID, frozen operations, awards and historical receipts are preserved.
Fresh authentication, current-generation deployment evidence and an explicitly
authorized activation ceremony would still be required later. H never executes
recognition, provisions a capability, activates production or creates keys.

## Explicit host CLI

Quiesce application/worker access and filesystem replacement first. Establish the
existing binding generation from trusted installation records or separately
authorized host inspection; do not guess it. Confirm that the incident really is
device-only drift, not a restore, copied file, different host or schema migration.
Use the exact existing absolute paths. The examples below are placeholders, not
actual PythonAnywhere paths and were not executed against a deployed installation.

```sh
python -B scripts/active/manage_recognition_administration.py preview \
  --target /absolute/existing/target.sqlite \
  --control /absolute/existing/control.sqlite \
  --key-file /absolute/private/existing-mfa.key
```

Review the preview and take its `target_sha256`. Then deliberately invoke:

```sh
python -B scripts/active/manage_recognition_administration.py rebind-filesystem-identity \
  --target /absolute/existing/target.sqlite \
  --control /absolute/existing/control.sqlite \
  --key-file /absolute/private/existing-mfa.key \
  --expected-generation 1 \
  --target-sha256 <exact-fresh-preview-sha256> \
  --operator <trusted-deployment-operator> \
  --reason 'Reviewed device-only drift from 52 to 55; same host, paths and inodes'
```

Replace `1` with the actual bound generation. Operator and reason must be explicit.
The existing key-file argument/configuration remains required by CLI conventions;
H does not create, rotate or expose that key, reset MFA, or relax protected-file
rules for later administrative authentication. No `--force`, allow-device flag,
activation option, browser endpoint, worker or automatic retry is added.

After success, normal strict identity inspection should work with generation N+1.
Old login/session/confirmation authority must not be reused. If acknowledgement
is lost, inspect the current binding/audit rather than guessing a new generation
and retrying. A stale expected generation deliberately fails.

An inode, host, path, schema or UUID mismatch is **not** repairable through H.
Investigate it using the appropriate separately reviewed restore/recovery process.
In particular, `advance-restore` remains separate and retains its strict control
identity check. H is not a general installation reset or restore bypass.

SQLite locks serialize database writers, not trusted host file replacement.
Quiescence and trusted host/filesystem semantics remain operational requirements;
the final observation check is not an anti-administrator filesystem sandbox.
No protection against deliberate target/control rewind by trusted administrators
or unreported metadata-identical changes is claimed.

## Validation

Tests use newly created synthetic target/control files and simulate only the
observed device-number change. Actual file copies/replacements exercise inode and
path rejection. Coverage includes schema/hostname/UUID/owner mismatches, wrong
generation/preview, no-op denial, authentication invalidation, concurrent/stale
calls, audit validity/rollback, second observation drift, strict normal checks,
CLI argument requirements, no web route, and invalidation of an activated G
fixture's approvals and rehearsal evidence without any writer invocation.

Validation passed: focused H tests **23 passed, 21 subtests passed** (9.96s);
full suite **1120 passed, 3 skipped, 1074 subtests passed** (358.74s).
`git diff --check` and explicit new-file whitespace checks passed. Network and
repository-database access were blocked during test runs.

No deployed rebind, production
database access, recognition execution, award, activation, key creation, external
service contact, commit or push is performed by this implementation task.

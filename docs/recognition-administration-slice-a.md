# Slice A: local administrative identity and installation control

The owner, authorized deployment/database administrators, application code and
host are trusted. These are application controls, not administrator-proof records.
This slice supplies authentication and confirmation data only. It cannot approve,
execute, correct, reconcile or activate recognition. All existing production writer,
authority and synthetic-provider restrictions remain in place.

## Inspection and actual callers

Before implementation the relevant boundaries were inspected:

| Existing boundary | Actual behavior/callers |
| --- | --- |
| `src/review/auth.py` | Email-link authentication: 20-minute hashed, one-use login tokens; email/source throttling; `reviewer_sign_in` issues and `reviewer_verify` consumes them. No existing TOTP implementation. |
| `reviewer_verify`, `reviewer_sign_out` in `src/api/app.py` | Verified login clears/recreates the signed Flask session; ordinary reviewer lifetime is 30 days. Logout clears that cookie. New hooks issue/revoke a separate server-side administrative primary-authentication reference. |
| `admin_dashboard.review_lead_access/owner_access` | Verified matching reviewer identity plus database role. Existing `/admin`, pilot-summary, reviewer-list and role-management routes use these checks. Review leads are not recognition administrators. |
| Role changes | Web role management permits reviewer/review-lead changes and forbids changing owners; `scripts/active/set_reviewer_role.py` is the trusted operator path. A new target trigger advances an authentication epoch on owner role/key/verification changes, including direct SQL updates. |
| CSRF | Existing auth/admin mutation routes use the session's `auth_csrf`. New control routes require a nonempty, matching ASCII token even in Flask TESTING; unknown JSON fields are rejected. |
| Configuration | Explicit `DMV_BUS_STOPS_DB`; no database fallback. Flask secret/cookie configuration remains unchanged. Administrative control/key paths are optional configuration, never permission. |
| Slice 6 control store | `execution_schema.control_definitions`, `install_control`, `check_control` describe an isolated v1 stop/block store. Local administration explicitly extends those exact definitions as v2; the old v1 checker is unchanged and rejects v2. |
| Slice 7 | Activation ledger/workspace is synthetic and signed; no production activation provider. It remains dormant and separate. No new activation method is implemented here. |
| Slice 5 | Reuse the pure schema fingerprint calculation and actual SQLite file observation. Do not instantiate the synthetic enrollment workspace or require an external continuity registry. |
| Recognition entry points | Historical `permanent.finalize` is called by the disposable rehearsal/tests, with no application issuance dispatcher. Live sealing and discrepancy issuance remain separately guarded. Explorer processing is independent. None is called by new administrative APIs. |
| Existing operation history | `operations.get_operation` verifies retained contracts/history. The new confirmation adapter reads these records only, with no arbitrary operation callback or decision writer. |

## Administrative identity and MFA

Installation explicitly pins one existing verified `owner` reviewer ID. A reviewer,
review lead, another owner account, URL access or browser-supplied actor cannot
become the installation's recognition administrator. Existing owner checks are
reused and repeated at sensitive boundaries.

Only successful consumption of an existing login link invokes
`record_primary_authentication`. The hook records a random hashed server-side
primary reference, actor, reviewer-key digest, target authentication epoch,
generation and times. Setting an `authenticated_reviewer_id` or `is_admin` field
does not create that reference. Misconfigured/unavailable administrative storage
does not prevent ordinary reviewer login; it prevents administrative authentication.

The installed `cryptography==50.0.2` package already includes standard TOTP and
Fernet encryption. It is now explicitly included in `requirements-pilot.txt`, but
no package was installed during this work. Crypto is loaded only for explicit MFA
operations, not app import. TOTP uses the library's SHA-1/6-digit/30-second standard
implementation, with a one-window drift allowance and durable last-used counter.
No custom authentication algorithm was written.

Enrollment requires a primary login less than 10 minutes old. The one-time setup
response contains an `otpauth` provisioning URI, necessary to provision Google
Authenticator; it has `Cache-Control: no-store`. It cannot be retrieved again.
The seed is never exposed after enrollment. Finishing setup requires a valid TOTP
and the same primary session, within 10 minutes. An expired pending setup can be
restarted; an enrolled seed cannot be replaced by another email login.

Only an encrypted seed is stored, in the separate control database. Encryption
also binds the seed payload to the actor and installation. No seed is stored in
the recognition database. The host-held Fernet key is read from an explicit file,
never generated by application startup or the installer. On POSIX its group/other
permission bits must be clear. On Windows the operator must establish suitable
ACLs; the code does not claim to verify Windows ACLs.

Failed TOTP attempts persist per-owner throttling: five failures block further
attempts in that 15-minute window, across connections and sessions. Valid codes
must advance the last-used time counter; enrollment verification consumes its
code too. Wait for the next code before opening an administrative session.

MFA recovery is a trusted-host ceremony only: `reset_mfa`/the explicit CLI clears
the encrypted seed, advances its epoch, revokes sessions and confirmations, and
audits operator/reason. Fresh owner login and deliberate enrollment are then
required. There is no email-only reset route or MFA-disable endpoint.

## Sessions, step-up and confirmations

Administrative sessions have an eight-hour absolute lifetime, independently of the
unchanged reviewer session. They are opaque browser references whose hashes and
validity are stored server-side. The primary proof lasts at most eight hours plus
the 10-minute session-establishment window; it does not extend an admin session.

Logout/re-login revokes the current primary proof and its administrative sessions.
If revocation cannot be persisted, logout returns 503 rather than reporting
successful server-side invalidation. Role demotion/re-promotion, reviewer-key or
verification changes invalidate sessions through the target epoch even if no
request occurred while the account was demoted. MFA reset and restore-generation
changes revoke sessions. Web requests also bind the administrative token to the
current browser's primary proof and verified reviewer identity.

Updated by Slice E: `create_step_up` requires a current, nonrevoked eight-hour
admin session and a new TOTP. It does not require another recent primary login
while that session remains valid. It records a hashed scoped token, session, action,
generation and 10-minute expiry bounded by the administrative session. Supported
scopes are approval, correction, recovery, activation, deactivation, suspension,
emergency-stop clear and MFA administration. Scoping one of these actions grants
no implementation of that action. Operation-specific scopes read and bind the
actual operation ID, envelope digest and current decision/execution/event state.

`begin_operation_confirmation` additionally requires an approval-scoped step-up.
It generates a random one-use token, stored hashed and bound to actor, session,
operation ID/digest, state digest, generation and expiry. Consumption re-reads the
actual operation and compares all bindings under the control writer lock. Changed
state burns the confirmation; expired, consumed, wrong-session or wrong-operation
tokens reject. Concurrent consumption succeeds once.

Consumption returns attributable confirmation DATA and writes an audit event.
It does not append an AUTHORIZED decision, mint a capability, or call execution.
Existing v1/v2 operation records are currently read-only inputs; Slice B must add
the production operation format and generation-bound approval record.

## Installation, target and restore generation

`LocalAdministration` requires explicit absolute target, control and host-key paths.
Runtime opens existing files only; it never creates a missing database. Target and
control must be separate files. Hard-linked database files are rejected.

Explicit installation creates one local target identity table and an owner-epoch
trigger, preserving existing recognition/Explorer tables. The target table records
installation UUID, target UUID, owner ID and authentication epoch. The control
binding stores actual path/host/device/inode observation, full SQLite schema
fingerprint (including application/user versions), control-file identity, generation
and a constant NOT_ACTIVATED state. A filename alone is insufficient.

Every administrative transaction verifies the exact schemas, control identity,
binding/audit chains, target observation/schema and target UUID/installation/owner.
Unexpected replacement, extra schema or wrong installation blocks access. The
physical observation is deliberately strict; PythonAnywhere multi-worker identity
stability still requires disposable deployment testing. There is no guessed host
or path exemption.

`advance_restore_generation` is a trusted-host API/CLI, not a web endpoint. It
requires the expected current generation, a digest from an explicit target preview,
operator and reason. It verifies the owner/schema, deliberately rebinds the target,
assigns a new target UUID, appends the next binding generation, invalidates primary
proofs/sessions/step-ups/confirmations and audits the action. State stays
NOT_ACTIVATED. Concurrent/stale generation or preview requests fail closed.

The control database is outside the target database, so restoring only the target
does not rewind its generation. Old operation/decision records are not rewritten.
There are no simplified-production approval records yet; Slice B must bind every
approval/operation to the current target UUID/generation and reject old pending
work. Existing synthetic operations cannot execute through these new controls.

This does not detect every unreported in-place restore retaining all metadata.
Restoring both databases deliberately is outside the threat model. Operators must
drain/pause relevant writers before restore/rebind and revalidate pending work.

## Schema, installation and CLI

The v2 control store reuses Slice 6's two stop/block tables and triggers. Eight
additional tables hold binding history, audit history, primary proofs, encrypted
MFA state, sessions, scoped step-ups, confirmations and attempt counters. Bindings
and audit history have contiguous sequences and immutable UPDATE/DELETE/REPLACE
triggers. No ordinary application role edits installation/generation history.

`administration_schema.install_control/install_target` require explicit caller
transactions and use savepoints; caught failures cannot commit partial DDL.
Installation is idempotent for the same installation UUID/owner/target binding.
The legacy synthetic v1 schema remains unchanged. Upgrading a v1 control file is
an explicit local-v2 migration, not something a synthetic executor can silently use.

Target and control are independent SQLite files. The installer/rebind commits the
target before control; these commits are not globally atomic. An interrupted
initial setup can leave target metadata without a control binding: retry explicit
setup with the SAME installation UUID. A failed restore/rebind can leave mismatched
metadata: runtime blocks until an operator previews and completes the rebind.
No partial configuration activates or authorizes recognition.

`scripts/active/manage_recognition_administration.py` exposes `preview`, `install`,
`advance-restore`, and `reset-mfa`. All paths are explicit; installation additionally
requires the installation UUID, verified owner ID, operator and reason. Creating
the separate control file requires `--create-control`; no key is generated. Restore
requires expected generation and preview digest. Reset requires explicit
`--confirm-mfa-reset`. No command invokes recognition, recovery or activation.

Operator configuration uses `RECOGNITION_ADMIN_CONTROL` and
`RECOGNITION_ADMIN_KEY_FILE`, plus the existing explicit target. These settings
select resources only; they do not grant administrative permission. Keep the key
outside the repository/static paths with restricted access and a separate protected
backup. Rotating a lost key requires deliberate MFA recovery/re-enrollment.

The locked operational policy is daily verified backups with 30-day retention for
target/control, with separately protected key recovery. No backup job or production
deployment is installed in Slice A; those procedures must be rehearsed later.

## Routes and downstream API boundary

The new prefix is `/api/admin/recognition-control`:

| Method / suffix | Function |
| --- | --- |
| GET `/identity` | Current owner primary identity, not an execution permission |
| POST `/mfa/enrollment` | Deliberate one-time setup URI |
| POST `/mfa/verify` | Verify and finish enrollment |
| POST `/session` | TOTP-authenticated admin session |
| GET `/session` | Current server-verified session identity |
| POST `/step-up` | Scoped recent TOTP proof |
| POST `/confirmations` | Begin exact-operation confirmation |
| POST `/confirmations/consume` | Consume confirmation data; explicitly `recognition_approved=false` |
| GET `/installation` | MFA-authenticated local installation metadata |

There are no reset, rebind, approval, execution, correction, recovery, activation
or stop-clear web actions in this slice. Actor identity is never accepted in request
JSON; unknown fields reject. Tokens and seeds are not logged. Control responses are
non-cacheable, errors use non-secret codes, and no arbitrary operation callbacks
or target-verification bypass parameters exist.

Slice B must validate the production operation/approval state, current generation,
and exact consumed confirmation. The returned JSON alone is not authority. Since
confirmation and future approval persistence may involve separate files, Slice B
must define failure/idempotency handling explicitly; consumed confirmation cannot
be blindly replayed to invent an approval after an uncertain request.

## Validation

Tests use fresh disposable targets, independent HMAC expectations/RFC 6238 vectors,
independent operation hashes and deterministic clocks. They exercise permission
denial, eight-hour/10-minute boundaries, replay/throttling, logout, role/key changes,
MFA reset, concurrent confirmation consumption, operation changes, target restore,
schema mismatch, migration savepoints, immutable history, secret-safe responses/logs,
startup isolation, reviewer compatibility, unchanged Explorer records and continued
production rejection.

Validation results:

- Focused administrative suite: **41 passed, 19 subtests passed**.
- Authentication/deployment and Slice 1–7 regression run before the final additional
  edge cases: **274 passed, 1 skipped, 268 subtests passed**.
- Final full `tests/` suite, including those edge cases and final audit checking:
  **929 passed, 3 skipped, 985 subtests passed**, in **200.52 seconds**.
- Tracked and new-file whitespace checks: no whitespace diagnostics.

The full test launcher installed audit hooks rejecting socket connections/DNS and
SQLite access under the repository's `src/database` directory. Tests used freshly
allocated disposable files and ephemeral synthetic MFA keys. Windows tests required
approved execution outside the restricted filesystem sandbox for temporary-file
access. No packages were installed, external services contacted, PythonAnywhere
accessed, production database opened, production award created or production
recognition/activation performed. No production key or external trust infrastructure
was created. No commit or push occurred.

Remaining deployment work is explicit local setup, protected host-key provisioning,
Windows ACLs where applicable, PythonAnywhere disposable validation and backup/restore
rehearsal. Slice B must add production approval contracts and their generation/state
checks; this slice supplies no production recognition authority. Trusted direct
database/deployment administrators remain outside the threat model.

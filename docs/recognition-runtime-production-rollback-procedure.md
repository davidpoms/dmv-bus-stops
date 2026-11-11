# Owner rollback procedure - PythonAnywhere recognition

For the project owner, confirmed as production custodian/deployment operator.
This is a procedure for a future authorized deployment or incident. Nothing is
executed by writing it. The compatible activation fix must be validated and
deployed before recognition activation.

## Protected installation stop after deploying the activation fix

Sign in afresh as the project owner and open
`/api/admin/recognition-control/owner-activation`. Authenticate with MFA, read
durable status, then use a new authenticator code to **Suspend** or **Deactivate**
the exact displayed installation/generation. Sign in afresh and verify the
persisted state. These actions invalidate old administrative credentials and
block further activated admission; they do not undo completed operations or
replace signed issuer-specific revocation. See the
[complete owner procedure](recognition-runtime-owner-activation-procedure.md).
If the response is uncertain, inspect status instead of resubmitting. If the
page or authentication fails, use the offline/maintenance procedure below.

## Before deployment

Have Codex record the correct PythonAnywhere app, current code/WSGI/environment
configuration, and verified backups of BOTH the application/target database and
recognition control database. Keep the approved package and a known compatible
code copy available. Store backups and secrets privately, outside the source
package. Do not post keys, login tokens or database contents in chat.

## If something goes wrong

1. **Stop new work.** Tell Codex: “Stop recognition; do not retry any operation.”
   Use the PythonAnywhere web-app disable/maintenance control for the affected
   app, and stop any separately running recognition job. Do not delete the app
   or its files. If you cannot isolate recognition safely, taking the affected
   web app offline is safer than allowing more work. If a job's status is
   uncertain, do not restart it. PythonAnywhere documents a disable operation
   separately from deletion in its [web-app controls](https://help.pythonanywhere.com/pages/API/).
2. **Keep the evidence.** Note the failure time and any displayed operation,
   authority/decision ID and error. Preserve current target/control databases,
   logs, backup records and configuration. Do not delete a journal, witness or
   “pending” record to clear the error.
3. **Revoke when appropriate.** For suspected key/account misuse, unexpected
   execution or an issuer that must not be used again, tell Codex to revoke that
   exact issuer using the existing authenticated owner/governance revocation
   process before any resumption. Revocation stops further permitted use; it
   does not undo committed changes or authorize a retry. If the normal controls
   fail, keep the app offline and escalate rather than editing the database or
   removing the trust file. Preserve the ability to inspect the outcome.
4. **Check the result before deciding what to restore.** Tell Codex: “Inspect the
   durable outcome of the original decision, read-only; do not execute again.”
   Codex uses the approved outcome-inspection mechanism with current authorized
   inspection credentials and the original ID. This inspection returns facts,
   not a new execution right. Do not use an “approve”, “create” or “execute”
   action as a substitute for inspection.

| Inspection result | What you should do |
| --- | --- |
| COMPLETED and target commit verified | The change happened. Do not repeat it, even if the response was lost. |
| TARGET_PENDING but target commit verified | The change happened; control recording is incomplete. Keep recognition stopped. Do not rerun it or repair records by hand. |
| Pending/unknown, missing proof, inspection error or no decision found | Do not assume nothing happened. Keep recognition stopped and ask for investigation. Absence of proof does not grant a retry. |

5. **Restore code/configuration only when compatible.** If the problem is the
   code deployment, have Codex check that the saved code can read the installed
   schema/journals before restoring that saved code and WSGI/environment
   configuration. Leave both live databases and their history intact. Do not
   reset secrets or activation settings as part of a code rollback. If schema
   changed and the old code is incompatible, do not force the old code back;
   keep the app offline with the compatible inspection code available.
6. **Do not automatically restore a database backup.** A backup can erase a
   successful effect or the record that prevents it being executed twice. Never
   restore just one of the two databases, drop journals or reset “spent” state.
   Database restoration requires a separate reviewed incident plan that preserves
   committed outcomes, identities and duplicate fences. Keep the current copies.
7. **Resume ordinary service only after checks; keep recognition stopped.** After
   compatible code/configuration restoration, Codex checks the actual database
   bindings, integrity, schema compatibility and ordinary application health.
   Reload/re-enable the web app only when safe. Do not start a new recognition
   run to test it. Recognition needs explicit permission before resuming.

## When to stop and escalate

Stop if you cannot identify the correct app/databases/original decision, cannot
verify a backup or result, see conflicting witness/control facts, cannot revoke
when needed, or the saved code cannot read the installed schema. Ask Codex for
read-only incident diagnosis, and PythonAnywhere support for platform/process
problems. Do not use repeated reloads or repeated recognition runs to resolve an
uncertain outcome.

## Technical reference for Codex, not owner work

- Inspection: `runtime_finalization.inspect_outcome(config, authority_id,
  approval=..., authority=...)`, with exact production inspection approval.
- Revocation: `runtime_finalization.revoke_issuer(...)`, with fresh owner
  authentication and the exact signed policy-bound revocation approval.
- No dedicated finalization-outcome/revocation CLI action is exposed by the
  current administration script; do not invent a command or browser button.
  Codex must prepare the exact supported API invocation after actual paths and
  authorized inspection/revocation context are available. No invocation is run here.
- Reload replaces worker processes; it does not restore an old process-local
  handoff. See [PythonAnywhere reload behavior](https://help.pythonanywhere.com/pages/ReloadWebApp).

No production action occurred in preparing this procedure. v1/120 default,
v2/300 prospective/test-only, the R30 authorization scope and all no-retry
boundaries remain unchanged.

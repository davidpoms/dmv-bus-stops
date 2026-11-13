# Owner activation and suspension

Use this procedure only after deploying the validated runtime-activation fix and
reloading the affected PythonAnywhere web app. The original R30 package alone
does not contain this page. No database migration or activation Bash command is
required by this fix. Keep `LIVE_RECOGNITION_CAPTURE=0` throughout this procedure.

## Activate

1. Sign out of the application, then sign in through its normal owner sign-in
   flow. Use your existing project-owner account.
2. On the same application, open
   `/api/admin/recognition-control/owner-activation` in your browser.
3. If MFA state is **UNENROLLED**, click **Set up MFA**. Add the displayed setup
   key to your authenticator (or use the provisioning URI with a compatible
   authenticator), then enter its six-digit code and click **Verify MFA setup**.
   The page reads durable MFA state again and must show **ENROLLED**. Keep setup
   details private; they are shown only during setup and cleared when the page
   is hidden or verification succeeds. Pending setup cannot retrieve its key
   again. Setup and verification require the same recent primary login; if
   `recent_primary_authentication_required` appears, sign out and sign in again.
   If setup was abandoned or its key was lost, wait for its ten-minute window
   to expire. Choose **Refresh MFA status** or reload the page. Expired PENDING
   setup exposes **Restart MFA setup**; sign in afresh before restarting. This
   uses the existing enrollment operation to replace the expired key and begin
   a new pending setup. It does not change durable PENDING to UNENROLLED.
   Hiding the page also invalidates any in-flight provisioning response, so
   returning to the tab cannot restore cleared setup details.
   No MFA reset or activation occurs in this setup flow.
   Wait for a **new** authenticator code after verification, because verification
   consumes the previous TOTP counter. Already-enrolled owners skip setup.
   Click **Authenticate with MFA** and enter your current authenticator code.
   Never paste the host encryption key into a terminal or share credentials.
4. Click **Read durable status**. Check the installation ID and generation
   against your deployment record. Stop if either is unexpected.
   Click **Check readiness**. Stop if prerequisites or issues remain; this page
   does not fabricate deployment rehearsal evidence or repair missing storage.
5. Wait for a new authenticator code, then click **Prepare activation**. Enter
   that new code. This first prepares a confirmation and displays fresh runtime
   readiness; it does not activate yet.
6. Read the displayed readiness. Accept the browser's exact installation and
   generation confirmation only if they match the intended installation, then
   enter the reason for your approval. This submits the protected activation
   transition. Success displays `"state": "ACTIVATED"`.
7. Sign out and sign in again. Reopen the page, authenticate with a new MFA code,
   and click **Read durable status**. Verify `activation.state` is `ACTIVATED`
   for the expected installation and generation. This is persisted status,
   verified independently of the earlier browser response.

Activation invalidates all earlier administrative sessions, step-ups and unused
confirmations in the same database commit. A fresh sign-in is mandatory.
Activation itself performs no recognition execution and grants no writer
capability. This procedure does not change live capture. Enabling capture is a
separate configuration action; it is not an activation substitute. No web reload
is needed for the activation database transition itself.

## Suspend or deactivate

Sign in afresh, open the same page, authenticate with MFA, and read durable
status. Wait for a new authenticator code. Click **Suspend** to stop recognition
admission, or **Deactivate** to revoke the installation's activated state. Check
the exact installation/generation in the confirmation and enter a reason.
Then sign in afresh, authenticate, and verify `SUSPENDED` or `DEACTIVATED`.

Both transitions revoke the old administrative continuations. Neither undoes
committed work, revokes a particular governance issuer record, or grants a retry.
This narrow path deliberately does not reactivate suspended/deactivated
installations. Existing issuer-specific revocation still requires its existing
signed governance approval; this page does not bypass that control.

## Failure or lost response

Do not repeat the state-changing request. Sign in afresh and read durable status.
If it is `ACTIVATED`, activation committed: do not activate again. If it is
`NOT_ACTIVATED`, activation is not recorded; stop for diagnosis rather than
automatically retrying. If status/authentication cannot be verified, stop
recognition jobs and keep the affected application offline until resolved.

Keep both databases, logs and the displayed IDs. Do not edit activation rows,
delete keys, restore a single database, or retry an uncertain recognition
operation. See the [owner rollback procedure](recognition-runtime-production-rollback-procedure.md).

No production access, deployment, authority issuance or activation occurs by
adding this procedure. v1/120 seconds and v2/300 seconds are unchanged.

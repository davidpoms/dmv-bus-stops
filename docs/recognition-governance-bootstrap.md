# Minimal operator governance bootstrap

This runbook is for an explicitly approved generation-5 bootstrap. Implementation
and tests do not authorize running these commands on production. The tool performs
nothing on import, defaults to no action, and never connects to a database or the
network. Existing runtime authentication, MFA, readiness, profile, physical identity,
completion and activation verification remain unchanged.

## 1. Generate locally, offline

Run `scripts/operator/recognition_governance.py` on the custodian's own machine,
disconnected from the network, **not PythonAnywhere**. `--confirm-offline` records
the operator's acknowledgement; software cannot prove a machine is disconnected.
Use the existing Python environment with `cryptography` installed. No private key
is created merely by installing/importing the tool or requesting help.

Windows PowerShell, from the repository, after explicit bootstrap approval:

Run these commands in a real interactive Windows Terminal/PowerShell window or
VS Code's **Terminal** panel. VS Code Output/Debug Console, Codex captured execution,
background jobs and redirected input are not secure passphrase-entry surfaces.
If the tool returns `governance_secure_terminal_required`, run the same command
interactively; do not provide the passphrase in arguments, environment variables,
a pipe or a file. No key/output is created when the first secure prompt fails.
The tool never falls back to echoed input.

```powershell
$govDir = Join-Path $env:USERPROFILE '.dmv-governance'
New-Item -ItemType Directory -Path $govDir -ErrorAction Stop | Out-Null
$operatorSid = [System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
icacls $govDir /inheritance:r /grant:r "*${operatorSid}:(OI)(CI)F"
if ($LASTEXITCODE -ne 0) { throw 'Private directory protection failed' }

& .\.venv\Scripts\python.exe -B scripts/operator/recognition_governance.py keygen `
  --private-key "$govDir\governance-private.pem" `
  --public-root "$govDir\governance-root.public.json" `
  --installation-id f5d48fcd-a8ce-45fb-ad5c-0009acaa7947 `
  --owner-id 144 --confirm-offline
```

The installation/owner values above are the reported existing deployment values;
confirm them against trusted generation-5 inventory before approving this operation.
Do not generate a new installation ID. If the directory already exists, stop and
inspect its protection and existing outputs; do not overwrite keys or reset ACLs.

On a POSIX operator machine, the equivalent protected directory is created with
`mkdir -m 700 "$HOME/.dmv-governance"`; use the same `keygen` arguments with absolute
local paths and the operator's existing Python interpreter. Do not run keygen on PA.

The tool refuses private-key paths inside this checkout or any Git repository,
symlinks, hard-linked files and insecure directories. On POSIX private permissions
must exclude all group/world access and belong to the executing operator. Windows
ACLs may allow only the verified owner/operator, SYSTEM, Administrators and owner
rights; broad user/group access rejects. Existing files are never replaced.

Two non-echoed prompts collect and confirm a passphrase of at least 12 characters.
There is no passphrase command argument or environment-variable option, and an
unsafe terminal echo fallback rejects. The private file is **encrypted PKCS#8 PEM**;
only its corresponding public key appears in the public JSON. Keep the private file
and passphrase in the custodian's protected offline custody. Backup/custody remains
an operator responsibility; this tool is not a recovery or key-management service.

Output is `state=GENERATED_OFFLINE` and `public_key_sha256`. This fingerprint is
SHA256 of the raw 32-byte Ed25519 public key, not a hash of the JSON file. Record
the actual fingerprint, custodian, installation/owner mapping and approval in the
deployment record. Do not add metadata fields to the root JSON.

## 2. Transfer and install only the approved public root

Using the existing PythonAnywhere Files UI or existing approved transfer process,
upload **only** `governance-root.public.json` to:

`/home/davidpoms/governance-root.public.json`

Never upload `governance-private.pem`, the whole operator directory, a passphrase,
or a key backup. The offline key is outside the repository and source/runtime
package; no tool command transfers files automatically.

After explicit approval of the actual fingerprint and root installation, run in PA
Bash from the deployed repository:

```bash
: "${APPROVED_PUBLIC_KEY_SHA256:?Set the approved offline public-key fingerprint}"
python -B scripts/operator/recognition_governance.py install-public-root \
  --source /home/davidpoms/governance-root.public.json \
  --control /home/davidpoms/recognition-admin-control.db \
  --installation-id f5d48fcd-a8ce-45fb-ad5c-0009acaa7947 \
  --owner-id 144 \
  --approved-public-key-sha256 "$APPROVED_PUBLIC_KEY_SHA256"
```

Type the same approved fingerprint when prompted. This operation needs no SQLite
loader: it imports no SQLite/application-runtime modules and opens no database.
It checks only the named control file's metadata to derive the existing root path.

The destination is exactly:

`/home/davidpoms/recognition-admin-control.db.governance-root.json`

The installer requires canonical five-field JSON, correct fixed format/mandate,
exact supplied installation/owner, canonical base64 raw 32-byte public key and the
approved fingerprint. The file and parent must satisfy the existing regular-file,
canonical-path, non-symlink, single-link and protected-write requirements. A fully
written, synchronized temporary public file is published exclusively; an existing
destination, including a symlink, is never replaced. The final file is mode 0600
on POSIX. Publication briefly has two links; the temporary link is removed before
success. Interrupted/uncertain installation must be inspected, not blindly retried
or automatically repaired. A leftover extra link fails existing runtime checks.

Success reports `state=PUBLIC_ROOT_INSTALLED` and the matching public fingerprint.
It does not change generation, bindings, profiles, authentication, schemas or
activation. Root installation is trust configuration, not execution authority.

## 3. Sign only a reviewed foundation request, offline

The signer accepts the existing complete governance body as a JSON input file;
it is not a live-state collector. Obtain the actual binding/physical observations,
current owner primary/admin-record hashes and credential-clipped timestamps from
trusted read-only inventory. Do not use invented values or copy raw browser tokens.
The signing tool does not generate sessions, MFA credentials or deployment evidence.

Prepare and independently review the body under the existing
[foundation authorization contract](recognition-runtime-target-schema-completion.md).
Only `target_event_foundation_preview` and `target_event_foundation_completion`
are supported. Other governance/issuance purposes are refused. The existing
canonical serialization, domain and signature encoding are unchanged.

On the offline operator machine, with `$govDir` as above and
`$reviewedPayloadFile` set to the actual reviewed request's absolute path:

```powershell
& .\.venv\Scripts\python.exe -B scripts/operator/recognition_governance.py sign `
  --private-key "$govDir\governance-private.pem" `
  --public-root "$govDir\governance-root.public.json" `
  --payload $reviewedPayloadFile `
  --output "$govDir\foundation-preview-authorization.json" --confirm-offline
```

Review the displayed purpose, payload digest and public fingerprint. Type the
reviewed payload digest, then enter the key passphrase privately. The signer
checks the key matches the public root, fixes the allowed purpose/package scope,
checks the existing 600-second signature interval, signs the exact canonical
body with the existing domain and locally verifies the signature. It writes only:

`{"serialized_approval":"<existing canonical body>","signature":"<canonical base64 signature>"}`

No private-key contents, passphrase, payload body or signature is printed. The
authorization file is protected and never overwritten. Upload only that signed
authorization file for the existing maintenance CLI. The actual CLI still checks
live MFA/admin scope, generation/profile/H0, physical identity, readiness and all
other existing prerequisites. An offline signature does not replace those checks.

Completion needs a separately reviewed exact-plan completion body and a different
output filename. This bootstrap does not run preview, completion or activation.

## Stop conditions

Any failure requires inspection of outputs before retry, particularly after a
filesystem/publication error. Do not regenerate over an existing private key,
replace an existing public root, copy test keys or bypass permission checks. No
rotation, revocation service, arbitrary signer purpose or root recovery is added.
The private key is not recoverable from the public root or its fingerprint.

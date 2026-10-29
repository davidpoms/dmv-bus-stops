# Slice 2b: read-only WSGI runtime evidence

This slice collects evidence for later explicit local enrollment. It creates no
runtime profile, authentication scope, approval, writer capability, readiness or
activation. Generation and NOT_ACTIVATED state remain unchanged. Ordinary v3
administration/execution still reject with runtime_profile_contract_not_enabled.

## Integration and deliberate arming

The application's private configuration accepts two **non-secret** values from
the trusted deployment operator:

- RECOGNITION_RUNTIME_CHALLENGE_ID
- RECOGNITION_RUNTIME_CHALLENGE_SHA256

Both must identify an existing Slice 2a challenge. Leave both unset normally.
Never put the plaintext nonce in configuration, a WSGI file, an environment
variable, a URL or a log. This collector neither accepts nor needs that nonce;
it binds evidence to the durable challenge and its nonce_sha256. Nonce possession
does not authenticate a worker. The operator retains the nonce separately for a
later ceremony, whose proof and approval contract is outside this slice.

src/api/app.py registers runtime_evidence.register_runtime_evidence with the
application's actual DATABASE_PATH accessor and RECOGNITION_ADMIN_CONTROL.
No administrative key path is passed to the collector. No HTTP route is added.

An armed hook runs once per PID/challenge ID/digest on an ordinary WSGI request,
after the existing deployment configuration checks. Importing/preloading the
application does not collect evidence. It runs in the serving process, rather
than the deployment console or preload master. Request bodies, headers, query
strings and browser identity claims are not inputs. A normal request can trigger
an already privately armed collection; it cannot arm or choose its scope.

Each process attempts an arm only once, including failures. Threads serialize
through a process-local lock. A new worker/restart can collect again. Re-arm or
restart deliberately after resolving a failed collection. Clear the configuration
after evidence capture. There is no production collector CLI.

## Checks and evidence format

All SQLite opens use URI mode=ro plus PRAGMA query_only=ON. Collection validates
exact control/target schemas, binding and audit chains, immutable challenge digest
and audit relationship, current generation/source binding digest, installation,
target UUID, owner, role, validity window and absence of a consuming profile.
It checks NOT_ACTIVATED, including applicable readiness state. No transaction
with write intent or administrative transaction is performed.

The existing target_identity and observe_target helpers supply actual identities
and target schema fingerprint. Target/control resolved paths and inodes must
match their deployment bindings; schema and logical installation metadata must
also match. Path and connection observations, and independent fresh snapshots,
must agree. Hostname must be nonblank/NUL-free and consistent between the two
actual observations. Device/inode values are lossless canonical decimal strings
in evidence, including unsigned values above SQLite's signed INTEGER range.

Runtime hostname/device are independently observed: they are deliberately not
required to equal the deployment namespace. For example, console host
blue-liveconsole13/device 58 and web host blue-liveweb36/device 60 can produce
different truthful observations. This is evidence collection, not an exception
to any ordinary identity check. Within-collection hostname/device/inode drift
rejects. There is no enrolled runtime identity yet against which to reject an
otherwise stable, newly observed hostname/device. That approval belongs to the
operator and later enrollment contract, never a hostname allowlist.

The private server log receives one structured line per attempt:

```text
RECOGNITION_RUNTIME_EVIDENCE {"observation":{...},"observation_sha256":"..."}
```

The observation format is recognition-runtime-observation-v1. Exact fields are:

- format, role
- installation_id, target_id, owner_id, source_generation, source_binding_sha256
- challenge_id, challenge_sha256, nonce_sha256, challenge_expires_at
- observed_at (integer UTC seconds)
- hostname, target_path, target_device, target_inode
- control_path, control_device, control_inode, target_schema_sha256
- pid, python_version, python_executable
- evidence_channel = operator-reviewed-private-wsgi-log-v1
- provenance = REQUIRES_OPERATOR_REVIEW

observation_sha256 is rules.digest of the complete observation: canonical JSON,
sorted keys, compact separators, ASCII escaping, SHA256 of UTF-8. Process metadata
is evidence, not a persistent credential. A different PID/time changes the digest.
Failures log only REJECTED, a fixed error classification and PID; no exception
text, database contents or configuration values. No evidence enters HTTP output.

## Trust boundary, replay and limitations

The record is **not a cryptographic attestation or an authenticated enrollment**.
Its digest detects content changes, not provenance. The evidence_channel names
the required later provenance channel; it does not assert review has occurred.
Authentication depends on the operator retrieving the actual worker record through
authenticated private provider access and explicitly reviewing/approving its
digest in a later local ceremony. An arbitrary copied JSON record, challenge ID,
nonce hash, hostname or signature-free log line is insufficient. If private-log
origin cannot be established, enrollment must remain blocked. This slice adds no
signing infrastructure and does not protect against compromised trusted code,
provider access, or an administrator fabricating application logs.

Collection does not consume challenges. Repeated or concurrent collection is
read-only and safe; each observation still needs fresh later validation. An
existing profile for the challenge rejects collection. Generation advancement,
expiry or binding changes reject stale challenges. Later enrollment must enforce
single consumption atomically using the existing unique/profile guards.

Independent read snapshots detect observed changes, but cannot reserve two
databases or prevent a change immediately after collection. Later enrollment must
recheck current generation, challenge, identities, expiry and revocations under
its own locking contract. A successful log is not readiness or permission.

Every future authorized worker must independently match the eventual enrolled
profile. Capturing one worker does not establish worker-population coverage.
Disagreement requires operator investigation; no worker enrolls itself. Similar
paths/inodes/UUIDs do not prove shared backing storage across namespaces; trusted
provider/deployment verification remains necessary. PythonAnywhere and production
have not been accessed or validated by this implementation.

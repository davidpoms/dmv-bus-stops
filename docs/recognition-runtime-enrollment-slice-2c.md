# Slice 2c: trusted local approval and initial runtime enrollment

This slice records a trusted deployment operator's explicit approval of runtime
evidence. It does not authenticate the runtime or enable ordinary v3 access.
Production remains NOT_ACTIVATED; runtime authentication, readiness, activation,
execution and writer provisioning remain blocked.

## Trust boundary

The sequence remains: deployment-issued challenge, actual WSGI observation,
authenticated private-log retrieval, explicit operator approval, local enrollment,
and only in future slices runtime authorization. There is no web enrollment route.

The unsigned observation/review digests establish exact content, not provenance.
The code cannot determine whether an imported file came from the provider's real
private log. The trusted operator must independently establish that provenance
and review the complete observations. Confirmation flags record that decision;
they do not authenticate anyone. Neither hostname/device strings, nonce possession,
evidence_channel nor provenance fields establish runtime trust themselves.

No console-side collection is used to manufacture or replace a worker observation.
The console strictly verifies its own existing deployment identities; the selected
worker hostname/device come from the independently reviewed evidence. Inodes,
resolved target/control paths, target schema and logical installation scope must
still match the source binding. All supplied workers must have identical physical
identity and challenge scope. No matching subset is silently selected.

## Local review envelope

Copy unchanged Slice 2b JSON evidence envelopes from the verified private log
(excluding logging prefixes) into this exact local transport envelope:

```json
{
  "format": "recognition-runtime-enrollment-review-v1",
  "observations": [
    {"observation": {}, "observation_sha256": "SELECTED_OBSERVATION_DIGEST"}
  ],
  "selected_observation_sha256": "SELECTED_OBSERVATION_DIGEST"
}
```

The empty observation above is a placeholder: every observation must contain the
complete, exact Slice 2b fields. Unknown/missing fields, duplicate JSON keys,
floating-point numbers, booleans used as integers, NULs, noncanonical UUIDs,
SHA256 values, decimal device/inode strings and physical paths reject. Process
metadata is bounded text preserved exactly; the worker executable is not resolved
in the console filesystem namespace. Evidence remains REQUIRES_OPERATOR_REVIEW;
do not edit it to APPROVED.

Limits: at most 32 distinct evidence envelopes, each at most 16,384 canonical
UTF-8 bytes; the input and canonical review must each be at most 262,144 bytes.
Hostname is bounded to 255 characters and process metadata/physical paths to 4,096.
Device/inode text is lossless, including values above signed SQLite INTEGER range.

The review digest is rules.digest(parse_review(serialized_review)); the selected
observation digest is the unchanged selected envelope's observation_sha256.
The entire review, selection and scope must be inspected before committing those
approved digests to the ceremony. The input file is untrusted comparison material,
not proof of authenticated retrieval. Retain no plaintext nonce in that file.

## One-command private-log review preparation

After authenticated retrieval of actual private WSGI evidence, prepare the review
and its two digests in one command, run from the repository root on PythonAnywhere:

```bash
python -B scripts/active/prepare_recognition_runtime_review.py \
  --private-log /absolute/private-wsgi-challenge.log \
  --challenge-id UUID --challenge-sha256 SHA256 \
  --expected-generation 4 --source-binding-sha256 SHA256 \
  --output /absolute/runtime-review.json
```

Use the actual generation-4 challenge ID, challenge digest and source-binding
digest returned by the existing challenge ceremony. Both file paths must be
absolute. The output must be a new, separate file; existing files, symlinks and
hard links are never overwritten. On POSIX the new file is created with mode
0600, subject to the operator's umask. This command opens no database and needs
neither a key file nor the private SQLite runtime configuration.

The input must be a private-log excerpt containing all observations to be reviewed
for this challenge, with the original `RECOGNITION_RUNTIME_EVIDENCE` marker and
unchanged JSON envelopes. Logging prefixes are accepted. Unrelated lines are
ignored; SQLite startup logs and unmarked JSON cannot supply runtime evidence.
Every marked line must be a valid observation matching the requested challenge,
generation and source binding. Malformed records, collector REJECTED lines,
invalid digests, duplicate observations and worker disagreement reject the entire
input. The command never silently filters out mismatched workers or old challenges.
Retrieve a challenge-specific excerpt through trusted provider access; investigate
disagreement or collection failures rather than removing inconvenient records.
Lines are limited to 1,000,000 bytes; the existing review/observation limits apply.

With one observation, selection is automatic. With multiple observations, inspect
the records and add `--selected-observation-sha256 SHA256` to select exactly one
existing digest. All supplied observations remain in the review, unchanged in
fields and values; JSON whitespace and key ordering are canonicalized. Selection
does not remove the requirement for all workers to agree on physical identity and
challenge scope. The existing `validate_observation()` and `parse_review()`
validators enforce the evidence/review contracts.

Stdout contains only a JSON object with `review_sha256` and
`selected_observation_sha256`. These are candidate values for the existing
`--approved-review-sha256` and `--approved-observation-sha256` arguments below,
respectively, **only after the operator independently reviews the complete
artifact and establishes private-log provenance**. The review digest is
`rules.digest(parse_review(serialized_review))`, not a raw file checksum.
The command neither approves nor enrolls anything, never manufactures an
observation, and leaves `REQUIRES_OPERATOR_REVIEW` intact.

This is artifact preparation, not a new collection mechanism. A verified SQLite
startup log does not establish a runtime observation. The existing WSGI collector
must already have been armed with the challenge ID/digest in trusted configuration
and triggered by a real request. If no genuine worker record exists, preparation
fails. Changing a console environment cannot arm an already running worker.
This command does not edit WSGI configuration, reload workers, issue a challenge,
or trigger collection. Provider configuration/reload work remains a separate,
explicitly authorized deployment operation when necessary.

The challenge lifetime remains 600 seconds. Preparation does not consult durable
challenge state, establish provenance, or guarantee freshness; the existing
enrollment ceremony performs those state/time checks and requires the hidden
nonce and both operator confirmations. Complete collection, retrieval, review and
enrollment within that window; use a new challenge and genuine new evidence when
the old challenge expires. Initial enrollment from generation 4 advances control
metadata to generation 5 and remains NOT_ACTIVATED. No production migration or
activation is part of this path.

## Explicit CLI ceremony

Use the existing trusted local administrative CLI:

```text
python -B scripts/active/manage_recognition_administration.py enroll-runtime-profile \
  --target /absolute/target.db --control /absolute/control.db \
  --key-file /absolute/existing-key --installation-id UUID --target-id UUID \
  --owner-id OWNER --expected-generation N --source-binding-sha256 SHA256 \
  --challenge-id UUID --challenge-sha256 SHA256 --evidence-file /absolute/review.json \
  --approved-review-sha256 SHA256 --approved-observation-sha256 SHA256 \
  --operator OPERATOR --reason REASON \
  --confirm-private-log-review --confirm-enroll-runtime-profile
```

The challenge nonce is requested through a hidden prompt. There is no nonce
argument, environment variable or nonce-file input. If echo cannot be disabled,
the ceremony fails instead of reading an echoed nonce. Only its SHA256 is compared
with the challenge; it is never persisted, returned or logged. Reviewed metadata
or operator/reason containing that plaintext nonce reject. The administrative key
path follows existing CLI conventions but its contents are never read. The review
file cannot alias the configured target, control or key file. CLI failures emit a
fixed message without input/exception details. A lost nonce requires a new challenge.

## Atomic state transition

Prerequisites are an exact existing v3 schema, valid complete binding/audit history,
explicit current generation and binding digest, matching installation/target UUID/
owner, strict actual deployment control/target observations, verified owner,
NOT_ACTIVATED state, and a null current runtime-profile pointer. No migration or
repair is performed. Initial enrollment only: replacement/rotation/recovery reject.

The transaction acquires control BEGIN IMMEDIATE, then the target reservation.
Target query_only is enabled after reservation; no target writes are performed
or committed. No lock is held while prompting for operator input. Fresh UTC time
is read after lock acquisition and again before commit. Every reviewed observation
must satisfy issued_at <= observed_at <= created_at < challenge.expires_at.
Commit-time clock rollback or expiry also rejects.

For source generation N, one control transaction/savepoint:

1. Inserts the immutable runtime profile at N+1 using the exact selected physical
   observations, challenge, approved observation digest, operator/reason and audit
   sequence. profile_sha256 covers every other profile field.
2. Revokes primary proofs/sessions, removes step-ups and marks confirmations used,
   following administration._invalidate. MFA seed/enrollment is not reset or read.
3. Appends INVALIDATED history for every effective APPROVED approval using the
   existing migration policy. Approval bodies and historical outcomes are not rewritten.
4. Appends a v3 binding at N+1 with the profile pointer and previous binding hash.
   Deployment observations, installation ID, target UUID and owner remain unchanged.
5. Appends runtime_profile_enrolled audit history containing approved review and
   observation digests, full bounded review evidence, source/destination binding
   digests, profile digest, generations and explicit review/approval decisions.
6. Validates exact schema/FKs/history and rechecks deployment observations, owner
   and expiry before control commit, while retaining the target reservation.

Profile insertion consumes the challenge through UNIQUE(challenge_id). The challenge
row is never modified. Deferred generation/audit relationships permit this atomic
insertion order. Failure rolls back profile, revocations, approval invalidations,
binding and audit together. Runtime-auth scope records are not created or changed.

Concurrent finalizers at N serialize: one may succeed, the other rejects stale state.
This applies to both identical and different challenges. All other N challenges
become stale. Duplicate enrollment never silently repeats or advances generation.
After an uncertain commit acknowledgement, inspect durable challenge/profile/binding/
audit history through trusted read-only tooling before retrying.

## What enrollment does not establish

Ordinary administration._binding still rejects v3 with
runtime_profile_contract_not_enabled, including a non-null enrolled profile.
No authentication, operation format, approval format, execution permission, writer
capability, readiness evidence or activation is created. Old frozen operations
are not made portable to another host or the new generation. No awards are created.
Historical operations, claims and receipts are not rewritten or undone.

Reviewed evidence is a bounded historical observation, not a remote commit-time
reservation. Later runtime admission must independently observe itself and match
the enrolled profile. Submitted matching workers do not prove population coverage;
provider inventory and private-log provenance remain operator/deployment obligations.
Similar paths/inodes/UUIDs do not independently establish shared backing storage.

Console identity drift, schema changes, restores, profile replacement and compromised
trust require separately reviewed recovery. Existing Slice H/restore helpers still
encounter the v3 gate; enrollment is not a bypass or recovery mechanism. No hosted
resource or production database is accessed by implementing or testing this slice.

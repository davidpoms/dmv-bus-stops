# Runtime-profile Slice 2a: local challenge issuance only

`runtime_challenges.issue_challenge()` is a trusted-host, deployment-only
ceremony. Host access authenticates the operator; operator/reason strings are
attribution, not credentials. No browser or HTTP route invokes it.

Prerequisites are an explicitly migrated exact v3 schema, valid binding/audit
history, exact expected generation and source binding SHA256, installation UUID,
target UUID, owner ID, strict deployment control/target observations and target
schema, verified project owner and NOT_ACTIVATED state. The administrative key
path follows existing CLI conventions but its contents are never read.

The ceremony takes BEGIN IMMEDIATE on control, then a target writer reservation
through the control commit. It performs no target mutations. It appends only an
immutable challenge and its audit record, revalidates schema and observations,
and commits atomically. Failure rolls back both appended records. No migration,
repair, generation advance or authentication changes occur.

Challenge IDs are random UUID4 values; nonces use 32 cryptographically random
bytes encoded with token_urlsafe. Only nonce_sha256 is stored. Expiry is exactly
issued_at + 600 integer UTC seconds. The challenge digest covers all other row
fields, including the audit sequence. The nonce is returned once after commit.

Example (placeholders must come from trusted inspection of the current store):

```text
python -B scripts/active/manage_recognition_administration.py issue-runtime-challenge \
  --target /absolute/target.db --control /absolute/control.db \
  --key-file /absolute/existing-key \
  --installation-id UUID --target-id UUID --owner-id OWNER_ID \
  --expected-generation GENERATION --source-binding-sha256 SHA256 \
  --operator OPERATOR --reason REASON --confirm-issue-runtime-challenge
```

Stdout contains JSON with `challenge` and `nonce`. Do not redirect or capture it
in persistent logs. No nonce output file or plaintext database field is created.
Loss of the returned nonce cannot be repaired from its hash; issue a fresh
challenge. After an uncertain commit, inspect durable history before retrying.

Two issuances against the same current generation serialize and may both succeed
with distinct challenges; issuing a challenge does not consume or advance that
generation. Old rows remain immutable. A later generation makes their source
stale; the existing Slice 1 profile guards reject their use for enrollment. This
slice implements no enrollment or consumption operation.

The separate deployment history reader does not change administration._binding,
transaction, _verify, target_identity or Slice H. Ordinary v3 administration and
execution still reject with runtime_profile_contract_not_enabled. This ceremony
is not runtime identity verification and does not resolve the console/WSGI
identity mismatch.

No WSGI collector, profile creation, runtime authentication, operation changes,
writer capability, readiness enablement or activation is included. Production
remains NOT_ACTIVATED. Profile collection, approval and enrollment require later
reviewed slices.

# Production-format trust and authority-status contracts (Slice 4)

This is a verification library and LOCAL/SYNTHETIC tests, not production
authorization. It does not create production authority or permit production
execution. Existing `authority.provision_production_authority()` still rejects
unconditionally. No writer, Flask integration, Explorer behavior, First Look
lifecycle, signing service, authentication, target enrollment, executor,
emergency stop, or commit/recovery coordinator is changed or added.

## Trust boundary and supplied inputs

`trust.SyntheticTrustProvider(configuration_json, max_status_age_seconds=172800,
minimum_sequence=0)` is the only available provider. Exact-type checks reject
callbacks, application roles, arbitrary objects, and the older synthetic artifact
verifier. There is no production provider, environment loader, default public key,
network transport, private-key loading, signing API, or Authority conversion.

Configuration is strict JSON with exactly:

- `registry_id`: independently supplied accepted authority-status registry identity.
- `authority_keys`: entries with `authority_id`, `key_id`, canonical Base64
  `public_key`, and `grants` containing explicit `{family, action}` pairs.
- `status_keys`: separate entries with `key_id` and canonical Base64 `public_key`.

Current grants support only the existing frozen historical-operation families
`first_look` and `geography_steward`, action `finalize`. This is not a general
authorization wildcard or standing production permission. The provider supplies
public-key/static-scope verification inputs; every authorization still binds one
exact operation. Public-key/key-ID reuse is rejected across identities and signing
purposes. Each authority has one key; rotation creates a new authority and key.
Historical authority and status public keys must remain available.

Public-key configuration is trusted input, not authenticated because it happens
to be JSON. The implementation only accepts the explicitly synthetic provider.
All private keys in tests are synthetic and remain in memory. Production trust
installation, owner appointment and later delegate appointment remain external
administrative responsibilities. Authentication establishes executive identity;
it does not establish this trust root. The Flask runtime must not hold unrestricted
production signing capability.

## Authorization artifact

`trust.authorization_payload(operation_json, artifact_id=..., authority_id=...,
key_id=..., registry_id=..., issued_at_utc=..., expires_at_utc=...)` constructs
unsigned canonical JSON. It never signs it or creates writer authority.

`operation_json` is the canonical **existing Slice 3 envelope**, obtained from
`operations.get_operation(...)["envelope"]` by a future trusted caller. Verification
does not open SQLite or independently certify that the supplied envelope was
retrieved from an authentic store. There is no second operation representation.

The payload has exactly `artifact_id`, `authority_id`, `key_id`, `registry_id`,
`operation`, `issued_at_utc`, and `expires_at_utc`. Artifact IDs are canonical UUIDs.
Issuance/expiry are mandatory; issuance must precede expiry. Global artifact-ID
uniqueness/consumption is an issuer/coordinator responsibility, not a verifier
side effect or replay ledger implemented here.

For a future Slice 3 history association, `artifact_id` maps to its existing
`authorization_id` reference, and the canonical complete signed envelope's SHA-256
maps to `artifact_sha256`. Verification does not write that history or mark any
operation AUTHORIZED.

`operation` retains exact envelope values for operation/event/preparation IDs,
family/action, dependency and writer-manifest digests, enrollment placeholder,
rule digest, population digest, and target observation. It also contains
`envelope_sha256` and `accounting_policy_sha256`. The complete envelope digest
binds revision lineage, event/preparation hashes, full rule identity/version,
candidate identities, provenance, timestamps, target and accounting details.
Canonical equality preserves exact JSON types, including nested target values.
Identical writer manifests in different revisions are not interchangeable.

Legacy Slice 3 v1 contracts remain `synthetic_contract_only: true` with
`{enrollment_id: null, generation: null}`. These placeholders are explicitly
unenrolled; neither a good signature nor valid status turns them into enrollment.
[Slice 5](recognition-enrollment.md) adds synthetic v2 operation contracts with
exact enrollment ID/generation/signed-record digest references. Trust verification
binds those references but does not itself verify current target enrollment.
Existing immutable envelopes are never rewritten to add enrollment.

The signed envelope has exactly:

| Field | Value |
| --- | --- |
| `format` | `recognition-authorization-v1` |
| `algorithm` | `Ed25519` |
| `payload` | The exact payload above |
| `signature` | Canonical padded standard Base64, 64 signature bytes |

Signature input is the ASCII bytes `DMV-recognition-authorization-v1`, one NUL,
then `rules.canonical(payload).encode("utf-8")`. Public keys have 32 decoded bytes.
This profile uses existing sorted-key, compact, ASCII-escaped JSON semantics;
existing evidence/operation hashing is unchanged. Duplicate keys, floats,
non-finite numbers, unknown fields and unsupported versions/algorithms fail.
Unicode is not normalized; existing ASCII escaping semantics are preserved.

## Independent verification facts

- `verify_historical_authorization(artifact_json, operation_json=..., provider=...)`
  verifies signature, exact operation binding, configured authority/key/registry,
  static action grant and a well-formed issuance interval. It does not check
  current status or present-time expiry. Its result is a historical cryptographic
  fact, not proof that an operation executed or that the issuer was permitted at
  the historical moment of signing.
- `verify_authorization_time(artifact_json, trusted_now_utc=...)` checks only the
  issuance interval. It does not check a signature. Its convention is
  `issued_at <= now < expires_at`; future issuance and exact expiry are rejected.
- `status.verify_status_signature(snapshot_json, provider=...)` verifies a separate
  signed status object without claiming freshness or updating checkpoints.
- `verify_current_authorization(...)` combines historical signature/binding, current
  authorization time, current signed status and rollback protection, then requires
  the authority and key both ENABLED. It returns immutable synthetic verification
  facts. It is **not execution admission**, does not consume approval, does not
  inspect event freshness/finality, and does not acquire a target mutation lock.

All core time checks use explicitly supplied canonical UTC whole-second time.
There is no wall-clock fallback. Neither verification result is an Authority or
Authorization, and both are rejected by existing writer APIs. Neither a signature
alone nor status alone satisfies the combined verification contract.

## Signed authority status

The status envelope uses the same four outer fields, format
`recognition-authority-status-v1`, algorithm `Ed25519`, and a distinct signature
domain: ASCII `DMV-recognition-authority-status-v1`, one NUL, canonical payload.

The payload has exactly:

- `registry_id`, UUID `snapshot_id`, separately configured status-signing `key_id`.
- Positive integer `sequence` (booleans are not integers).
- Canonical UTC `issued_at_utc` and `expires_at_utc`.
- `authorities`: one entry for every configured authority/key, each containing
  `authority_id`, `key_id`, `state`, and `key_state`. Each state is ENABLED or
  REVOKED. Missing, duplicated, conflicting or unknown entries fail closed.

Authority revocation and key revocation are separate current facts. This slice
does not invent deployment-status or enrollment-status records: Slice 3 has no
deployment identity and only an unenrolled placeholder. Those controls must be
added with actual enrollment/deployment contracts before production use.

## Freshness

`verify_current_status(snapshot_json, checkpoint_conn=..., trusted_now_utc=...,
provider=...)` requires all of:

1. A valid signature from a configured status key and the accepted registry.
2. `issued_at <= now < expires_at`.
3. `now - issued_at < max_status_age_seconds` (default 172800, exactly 48 hours).
4. Sequence at least the configured and durable accepted floors.

The exact freshness boundary is **exclusive**: exactly 48 hours old is stale.
The earlier of explicit expiry and the freshness limit blocks verification.
The setting is configurable independently of signature verification. This models
the accepted approximately 1–2 day revocation propagation window, not instantaneous
revocation or an online query guarantee. Missing/expired/unverifiable status fails.

## Durable rollback checkpoints

`status.install_checkpoint(conn)` explicitly installs a dedicated checkpoint store
in a new disposable file, under a caller-owned transaction. It is savepoint-safe
and does not commit. Installation rejects application schemas, extra tables or
triggers, attached databases, and in-memory stores. It never opens a target.

Current-status verification requires an idle explicit connection to this isolated
file. It owns `BEGIN IMMEDIATE` through commit, uses `synchronous=FULL`, and atomically
persists registry identity, sequence, full signed snapshot/hash and accepted
supplied time. Concurrent calls therefore compare against a serialized durable
floor. Failures roll back; there is no implicit reinstall/reset/fallback.

- Lower sequences fail, including after a genuine subprocess restart.
- Different content/signature at the same sequence fails; identical replay is
  accepted while fresh and can advance the observed-time floor.
- Accepted time cannot regress after restart.
- Higher sequences require a new snapshot identity and non-regressing issuance.
- Accepted authority/key revocations cannot be reversed by a later snapshot.
- Previous stored status is reverified and its digest/sequence checked. Expiry of
  that historical checkpoint snapshot does not erase its rollback/revocation floor.

A signed revocation snapshot is durably accepted even when the subsequent current
authorization check refuses a revoked authority. It cannot then be replaced by an
older enabled snapshot. Historical signature verification never changes this store.

This is a persistent **synthetic** checkpoint implementation, not production
rollback-resistant infrastructure. Deleting/restoring the entire checkpoint file,
privileged modification, trust-configuration compromise and false supplied time
remain outside its protection. The configured minimum sequence is an additional
independent floor. Protected storage, backup/restore rules, bootstrap evidence and
trusted time are production prerequisites; ordinary SQLite alone is not the trust
root and does not coordinate external authorization with target mutation.

## Rotation and historical retention

Authority A's historical artifacts remain verifiable using retained public key A.
A newer status may revoke A and enable new identity/key B. Current verification
then rejects A (including newly signed artifacts) and may accept B for its exact
operation. Old artifacts and operation histories are never rewritten.

Trusted configuration may add B while retaining A. The old checkpoint snapshot is
verified against its historical subset of known identities; the new current
snapshot must cover the complete expanded configuration. Removing required
historical keys or attempting to re-enable revoked A fails. Status-root rotation
similarly requires retaining keys needed to verify stored historical snapshots.

## Synthetic separation and remaining work

`artifacts.py` remains the older, separate synthetic profile. Its domain, verifier,
enrollment fixtures and results cannot enter the new trust provider or become
production authority. Production writers and Flask import neither new module nor
the synthetic artifact verifier as authorization. App roles/rows are not trust
inputs. Valid test keys cannot become production keys through any runtime loader
because none exists. This is an application boundary, not a sandbox against
arbitrary Python execution.

Tests use ephemeral synthetic keys, an independent published RFC 8032 signature
vector, independently assembled signing bytes, actual Slice 3 disposable operation
envelopes, and disposable checkpoint files. Restart tests use a new Python process
with only public configuration and signed data. No external services are contacted.

REQUIRES EXTERNAL INFRASTRUCTURE: independently administered production public-key
trust, executive identity/reauthentication and signing service, authenticated status
publication, protected checkpoints/minimum sequence distribution, historical key
retention, reliable time, and enrollment/deployment administration. Runtime signing
keys, production provisioning and activation remain unavailable.

REQUIRES IMPLEMENTATION DESIGN: Slice 5's authenticated target/enrollment extension,
and later execution admission, operation consumption/idempotency and commit/recovery
coordination. This slice does not close the authorization-to-commit race. No
repository blocker prevents continuing with Slice 5's disposable contract work.

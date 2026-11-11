# Slice 4e-11-1: AUTHORIZED genesis evidence

This is the normative clarification of the mandatory genesis `evidence` member
in the [4e-11 authority contract](recognition-runtime-activation-bound-authority-contract-4e-11.md).
It defines one closed evidence type, not a producer or a storage implementation.
No authority, schema, lifecycle record, authentication, writer, target effect,
receipt, recovery or activation is created by this slice.

## 1. Exact type and fields

The evidence is an ordinary JSON object, with **exactly three required fields**:

| Field | Exact type and constraint |
| --- | --- |
| `format` | JSON string, exactly `recognition-runtime-authorized-genesis-evidence-v1` |
| `authority_id` | JSON string, canonical lowercase hyphenated UUID, exactly the referenced authority body's UUID |
| `authority_sha256` | JSON string, exactly 64 lowercase hexadecimal characters, exactly `digest(authority_body)` |

`format` is both the object-type discriminator and version identifier. There is
no additional `type`, `state`, `version`, extension map or optional member.
Every field is non-null. Arrays, scalars, null, absent/extra fields, subclass-like
coercions and wrong types reject. No implicit stringification, trimming,
case-folding, UUID normalization or default values are permitted.

This deliberately repeats only authority identity and its complete body digest.
All other scope already has an exact canonical representation in 4e-11. Adding
independently supplied copies of that scope would introduce competing sources
of truth without adding proof.

## 2. Canonical encoding

Use the repository's existing rules, without introducing a new serializer:

- `rules.canonical(value)` is `json.dumps(value, sort_keys=True,
  separators=(",", ":"), ensure_ascii=True)`.
- Canonical bytes are that string encoded as UTF-8, without BOM, leading/trailing
  whitespace or newline. The evidence object's serialized key order is
  `authority_id`, `authority_sha256`, `format`, irrespective of construction order.
- Parse with the duplicate-key and numeric rejection behavior of `trust.load()`;
  require the exact field set with `trust.fields()`. A duplicate field rejects
  even if both values are identical. Re-encode and require byte-for-byte canonical
  equality; alternate escapes/order/spacing are not alternate canonical records.
- UUID validation follows `trust.identity()`: string equality to `str(UUID(value))`,
  including lowercase, hyphens and canonical length. UUID creation remains the
  authority producer's job; parsing never generates or repairs an ID.
- SHA256 validation follows `trust.sha()` / `runtime_profile_schema._check_sha()`:
  full match `[0-9a-f]{64}`. No uppercase, prefix, suffix, embedded/trailing NUL,
  whitespace or truncation is accepted.
- The three permitted values contain only their specified ASCII characters.
  Therefore raw or escaped NUL and C0/C1 control characters, including newline,
  carriage return and tab, reject in keys and values. No Unicode normalization
  or equivalent-looking Unicode identifier is accepted.
- No numbers, booleans, enum aliases or nulls occur in this object. The only
  evidence enum/tag is the exact `format` string above.

The enclosing authority/event retain their existing strict canonical integer,
UUID, SHA, path, depth and size rules. In particular timestamps are canonical
whole-second UTC `YYYY-MM-DDTHH:MM:SSZ` using `trust.utc()`; physical integers
and decimal text remain lossless. This evidence introduces no alternate encoding
or weakening of those nested contracts. Existing parser bounds remain in force;
the closed fields themselves have fixed canonical lengths.

## 3. Construction and digest graph

Let `A` be the fully validated canonical
`recognition-runtime-execution-authority-v1` body defined by 4e-11. Define:

```text
A_sha = digest(A)
E = {
  format: "recognition-runtime-authorized-genesis-evidence-v1",
  authority_id: A.authority_id,
  authority_sha256: A_sha
}
G.evidence = E
G_sha = digest(G)
```

This notation specifies construction, not an implemented API or a fixture
authorized for execution. Call `digest(A)` on the object, never
`digest(canonical(A))` (which would hash a JSON string instead of the body).
`rules.digest()` is SHA256 of the canonical UTF-8 bytes, returning lowercase hex.

If a detached evidence digest is needed for comparison, it is exactly
`digest(E)`. It is not a field in E, a new database column, a signature or an
additional authorization credential. The enclosing event digest already covers
the full E object. No evidence field is excluded from either digest.

The dependency graph is acyclic: A contains neither E nor G nor the issuance
audit digest. E references A; G contains E; the issuance audit references A_sha
and G_sha. Do not put a future event/audit/seal digest into A or E.

## 4. Exact enclosing genesis and audit binding

Evidence parsing validates shape/content linkage only. A valid durable genesis
additionally requires the complete 4e-11 graph, including all these equalities:

1. G is `recognition-runtime-execution-lifecycle-event-v1`, sequence **1**, state
   **AUTHORIZED**, kind **AUTHORIZE**. Its exact outer field set remains the one
   in 4e-11, with E as its mandatory `evidence`.
2. `G.authority_id = E.authority_id = A.authority_id = authority_row.authority_id`.
   `G.authority_sha256 = E.authority_sha256 = digest(A) = authority_row.body_sha256`.
   Authority JSON must itself be canonical and match every indexed column.
3. `G.operation_id` and `G.operation_sha256` equal A's exact
   `operation_reference.operation_id` and `.operation_sha256`; they must match
   the durable operation/proposal and ACK, not merely caller-provided strings.
4. `G.actor_id = A.authentication.actor_id = A.runtime_target.owner_id`; it is an
   exact positive integer, not bool/float. `G.reason` equals the exact validated
   `A.producer_ceremony.reason`. No substituted operator or inferred reason.
5. `G.at_utc = A.issued_at_utc`, with matching integer UTC row timestamps.
   `G.previous_sha256`, `G.entry_sha256`, `G.seal_sha256` and `G.receipt_sha256`
   are explicitly present **null** values. No predecessor, target entry, commit,
   receipt or seal is claimed by genesis.
6. The authority and genesis row reference the same issuance audit sequence.
   Its action is `runtime_execution_authority_issued`, actor equals G's owner,
   time equals G's time, and its exact subject is
   `{authority_id, authority_sha256, event_sequence, event_sha256}`, matching
   A/G and their recomputed digests. `event_sequence` is integer 1. Validate
   the existing complete append-only audit sequence and predecessor chain.
7. The typed producer step/confirmation artifacts, exact reviewed subject,
   confirmation row and immutable consumption audit must satisfy 4e-11,
   including one-use matching and original deadlines. A valid-looking genesis
   without that graph is rejected, not accepted as a newly issued authority.

These rules are for the initial event only. They do not define evidence for any
later state, authorize insertion, or extend manager-owned transaction semantics.
The future producer must revalidate fresh scope under the control reservation
and target query-only reservation and commit control before releasing target,
exactly as 4e-11 requires. No database or audit write API is implemented by this
clarification.

## 5. Binding inventory: copied, referenced and revalidated

Every scope item below is bound through **the entire A body digest**, not a
caller-selected projection/subset hash. None is copied separately into E.

| Item | Representation and authoritative comparison |
| --- | --- |
| Authority identity | Directly copied `authority_id` plus `authority_sha256` in E; exact A/G/row/audit comparisons |
| Operation identity | Derived from A.operation_reference; compared to G's outer fields and the exact durable operation |
| Operation/manifest digests | A.operation_reference.operation_sha256 and writer_manifest_sha256; resolve and verify canonical envelope/archived preparation |
| Target and physical observations/schema | A.runtime_target.target_id and A.physical_snapshot; exact current target/profile/schema/connection/path checks at production, not evidence-supplied overrides |
| Runtime profile | A.runtime_target.runtime_profile_sha256; validate complete enrollment/history and actual runtime observation |
| Generation and installation | A.runtime_target.generation and installation_id; compare to current binding/profile/target metadata |
| Owner | A.runtime_target.owner_id and A.authentication.actor_id; compare to G actor and current owner access |
| Auth/MFA epochs and credentials | A.runtime_target.auth_epoch/mfa_epoch and A.authentication primary/session hashes; existing current linkage/revocation/expiry readers remain authoritative |
| Activation incarnation/event | A.activation.sequence and event_sha256; resolve the exact existing activation event and ceremony, require the current validated head, no new counter |
| Runtime v2 approval | A.approval approval_id/approval_sha256/effective_history_sha256; current effective v2 reader and exact operation/scope comparison |
| Proposal identity | A.operation_reference operation/event/preparation IDs and digests; no new proposal identifier or portable wrapper |
| ACK identity | A.operation_reference.proposal_reference, including exact operation and acknowledgement sequence/digest; use the complete 4b-1 comparison |
| Dependencies | A.dependencies.snapshot and snapshot_sha256; verify original binding and current READY state/whole-population writer preconditions |
| Emergency stop | A.emergency_stop snapshot/digest; validate current stop history and absence of an operation block under reservation; stale stop evidence is not an exemption |
| Readiness | A.readiness assessment_sha256/assessed_at_utc/policy, resolved to the reviewed protected assessment binding; independently recompute according to 4e-11 |
| Issuance time | A.issued_at_utc, additionally equal to G/audit time; no extra evidence timestamp |
| Expiry | A.expires_at_utc and lifetime_policy; no evidence-specific expiry or duration |

No binding-critical field is excluded from A_sha merely because it is freshly
revalidated. Conversely, inclusion in A_sha never makes a mutable fact current.
Historical integrity checks may still succeed after expiry/revocation; they
must not masquerade as current admission or make immutable history unreadable.

## 6. Meaning and lifetime

AUTHORIZED genesis evidence means that the legitimate future authority producer
accepted the approved activation-bound scope when A was created, **provided** the
complete durable authority/consent/genesis/audit graph validates. E alone proves
only canonical content linkage. It is unsigned; it is not remote attestation,
MFA proof, a login credential or a self-authenticating enrollment document.
Authenticity relies on the approved trusted-host/control-store/owner-ceremony
boundary. Recomputing hashes on detached data cannot recreate that boundary.

Preserve the 4e-11 lifetime exactly:

```text
lifetime_policy = "recognition-runtime-authority-lifetime-120s-v1"
expires = min(issued + 120,
              primary expiry, session expiry,
              producer step expiry, producer confirmation expiry)
issued < expires <= issued + 120
```

Evidence contains no copied issue/expiry timestamp, duration, deadline override,
monotonic reading, PID, thread, executable or Python version. Issue/expiry and
policy are committed through A_sha; issuance time is also checked against the
outer event/audit. Fresh wall/monotonic checks remain in the future genuine
manager. Current use requires `now < expires`, valid clocks and all current
scope predicates. Historical parsing never renews or extends authority.

Activation change/end/reactivation, profile/generation/install/target mismatch,
owner or auth/MFA epoch changes, revocation, dependency mutation or changed stop
history make old authority unusable under the unchanged 4e-11 rules. No new
lifetime or automatic replacement policy is introduced.

## 7. Security invariants and exclusions

- Retargeting any bound input changes A_sha; using a replacement A must fail
  the immutable authority, ceremony, operation/ACK, genesis and audit checks.
  Computing a new digest does not authorize a new record.
- E cannot select another activation, profile/generation/install/owner/epoch,
  operation/manifest, approval, ACK, dependency set, stop state or deadline.
- Readiness and stop must be freshly checked; historical hashes cannot bypass
  either. There is no `ready`, `execute`, `committed`, `completed` or `recovered`
  flag in E and no hidden default granting such a condition.
- A 4d-1 claim is not a 4d-2 handoff, 4e-6 activated admission evidence, or 4e-11
  authority. A 4d-2 handoff and 4e-6 observation are also not authority. None
  converts into E or A; no such object/digest is added as a field or predecessor.
  In particular 4e-11's any-4d-1-claim exclusion for the operation is preserved.
- The new owner consent references the exact v2 approval and proposal/ACK; the
  old approval's `execution_authority=False` meaning remains unchanged. Its
  spent confirmation is never reused as the authority producer confirmation.
- E exposes no connection, SQL, writer, lease, execution, completion or recovery
  interface. Persisted JSON/digests cannot recreate a live process-local attempt.
- Excluded from E: tokens/TOTP/keys/seeds/ciphertext, runtime executable/version,
  process/thread/monotonic state, duplicate scope copies, claim/handoff promotion
  references, target entry/commit markers, writer results and receipts/seals.
  These exclusions do not remove any scope required in A or its producer checks.

## 8. Later states and exact 4e-12 dependency

**Only AUTHORIZED genesis evidence is defined by this slice. All later lifecycle
evidence types are rejected/unsupported until separately reviewed and specified.**

That includes EXECUTING, COMMITTED, COMPLETED, FAILED (including the existing
planned FAILED_BEFORE_COMMIT label), RECOVERY_REQUIRED and UNCERTAIN. Do not add
placeholder evidence tags, generic dictionaries, null evidence, permissive enum
fallbacks or codecs for them. The 4e-11 planned transition diagram is not an
implemented later-state codec or permission to accept those events now.

4e-12 is the next implementation boundary: authority storage/canonical codecs
and explicit manifest-aware local migration only. Use this closed E schema and
its exact genesis/A/G/audit binding rules for the mandatory event evidence field.
The initial storage readers/guards must accept only the specified genesis and
reject later-state insertion/parsing; future support requires a separately
reviewed schema/codec version transition. No future-state placeholder records.

Initial state/kind constraints are AUTHORIZED/AUTHORIZE only. Planned later
names are not accepted storage variants or placeholder evidence schemas.

Future focused tests must cover every E field/type, duplicate/unknown key,
canonical byte/digest mismatch, wrong referenced authority, cross-authority E/G
substitution, mismatched outer operation/actor/reason/time/null fields, missing
ceremony/audit/authority graph, unchanged original expiry and denial of every
later state. Synthetic schema fixtures remain test-only data, not capabilities.

This clarification resolves the missing genesis evidence shape; it does not
implement or preapprove the eventual 4e-12 code. The other approved 4e-11
storage, migration, immutability and zero-authority requirements remain intact.

## Validation

The four requested existing test files ran once under disposable database and
network guards: **75 passed, 256 subtests passed in 702.45 seconds**. They cover
activated owner, claim consumption, execution admission and operation contract.
No new codec fixture or production provider was added. These existing tests
verify unchanged behavior; they do not prove the unimplemented genesis codec or
producer. No recognition/deployment family or full suite ran.

`git diff --check` and both documents' whitespace checks pass. Python source
matches the prior fingerprint exactly. Only this document and the necessary
4e-11 cross-reference changed; all preexisting working-tree changes remain.
Tests use existing disposable fixtures, not hosted/production databases or real
deployment keys. No authority/schema implementation, hosted/production access,
commit or push occurred.

**A. APPROVE 4e-11-1 — AUTHORIZED genesis evidence contract complete.**

The next implementation boundary is **4e-12**, subject to its existing scope
and review gates: canonical codecs, immutable control-side storage and explicit
manifest-aware local migration, with zero authority issued and no downstream
writer/execution/readiness/activation capability enabled.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED

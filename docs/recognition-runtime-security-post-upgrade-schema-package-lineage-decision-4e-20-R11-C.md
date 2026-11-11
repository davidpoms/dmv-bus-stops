# R11-C — post-upgrade schema-package lineage compatibility decision

## 1. R11-B blocker and scope

[R11-B](recognition-runtime-security-versioned-lifetime-migration-implementation-4e-20-R11-B.md)
identified a missing rule for attempt or enrollment-transition storage installed
after the lifetime-policy upgrade. Their installers record actual successor
schema hashes, while current validators require the original prerequisite
package's installed hash as the direct predecessor.

This decision amends [R10 section 9](recognition-runtime-security-versioned-lifetime-compatibility-migration-design-4e-20-R10.md)
for that case. [R11-A's main-staging amendment](recognition-runtime-security-versioned-lifetime-migration-design-amendment-4e-20-R11-A.md)
is unchanged. This document specifies compatibility only: no implementation,
migration, package installation, database access or policy activation occurs.

## 2. Existing lineage semantics

The actual sources inspected are:

- [Attempt storage](../src/review/recognition/runtime_execution_attempt_schema.py):
  `migrate()`, `check_manifest_transition()`, `authority_manifest()` and package constants.
- [Enrollment-transition storage](../src/review/recognition/runtime_enrollment_transition_schema.py):
  `migrate()`, `historical_manifest()`, package definitions and identities.
- [Authority storage](../src/review/recognition/runtime_activation_authority_schema.py):
  original migration audit, predecessor checks and claim-manifest projection.
- [Raw manifest](../src/review/recognition/runtime_execution_claim_schema.py): `manifest()`.
- [Administrative owner](../src/review/recognition/administration.py): `_audit()`,
  `_audit_head()`, connection ownership and transaction cleanup.
- [Exact control validation](../src/review/recognition/administration_schema.py):
  object-set/SQL checks, isolation and extension validation.

**Existing assertion: C — both exact historical predecessor identity and installed
schema identity.** The attempt audit binds its actual before/after object maps;
the validator checks those hashes against schema projections and also requires
its previous hash to equal the original authority-install audit's installed hash.
The transition package makes the analogous assertion against the attempt audit.
These are exact equalities plus prerequisite audit ordering, not a general
compatibility permission. Known later additive packages are already projected
out to reconstruct earlier installation states.

The immutable administrative audit chain checks sequence continuity, body digests,
previous-body digest links and nondecreasing times. Typed migration readers also
check migration identity, subject shape and historical installation/binding scope.
That evidence is required in addition to schema hashes; a hash alone proves no
operator entitlement. The trusted-host/deployed-code boundary remains unchanged.

## 3. Hash meanings and package identities

Define `H(M)` as the existing `digest()` of the complete name-to-SQL map with each
SQL string normalized by `' '.join(sql.split())`. Do not change normalization,
digest, object names or exclusion rules for raw current manifests.

| Value | Meaning |
| --- | --- |
| `previous_schema_sha256` | Actual complete stable schema immediately before that migration's DDL, in its reserved transaction. |
| `installed_schema_sha256` | Actual complete stable schema after that migration's DDL and staging removal, before commit. |
| Raw `claims.manifest()` | Actual current complete schema, including the lifetime replacement if installed. |
| Historical reconstructed hash | The exact schema state at one independently verified migration edge; it is not current schema authority. |

The existing six-field migration subject remains unchanged: migration ID,
previous/installed hashes, installation ID, generation and reason. No lineage
table, extra audit row, new subject field or new package format is needed.

Use these closed identities and definition sets:

| Symbol | Migration ID | Audit action | Effect |
| --- | --- | --- | --- |
| A | `recognition-runtime-activation-authority-storage-v1` | `runtime_activation_authority_schema_installed` | Existing authority/lifecycle definitions. |
| T | `recognition-runtime-execution-attempt-storage-v1` | `runtime_execution_attempt_schema_installed` | Existing attempt/history definitions. |
| E | `recognition-runtime-enrollment-transition-storage-v1` | `runtime_schema_transition_storage_installed` | Existing enrollment-transition definitions. |
| L | `recognition-runtime-authority-lifetime-policies-v2` | `runtime_authority_lifetime_policy_schema_upgraded` | R10's exact authority table and scope-guard replacement only. |

L is the proposed migration-support identity from R10, not evidence that it exists
or that v2 has been adopted. T/E definitions and data-format meanings do not change
merely because they are installed after L.

## 4. Candidate compatibility models

| Candidate | Authority and recorded/accepted hashes | Rollback, stale-package and unauthorized-change treatment | Decision |
| --- | --- | --- | --- |
| A — Additional explicit lineage record | Would require another durable record and its independent relationship to existing typed audits. | Would need new atomic recording/recovery semantics; duplicate metadata cannot self-authorize. | Not needed; existing migration audits already record both hashes. |
| B — Explicitly enumerated transitions | Existing immutable typed audits, exact reviewed definitions and historical binding checks establish the path. Record raw hashes; accept only hashes recomputed for every permitted edge. | Transactional rollback preserves the prior valid prefix; missing, extra, altered or out-of-order edges reject. | Selected. |
| C — New package version | Could distinguish a successor package, but would require specifying a new identity/DDL and its installation rules. | Old/new exact definitions would still need an authenticated lineage. | Larger change; T/E DDL is unchanged, so versioning them does not solve the predecessor proof alone. |
| D — Existing projections alone | Current exclusions reconstruct additive history but do not distinguish whether L preceded or followed an installation. | Blind substitution would misinterpret recorded raw hashes. | Insufficient alone; retain projections only within B's verified ordering. |
| E — No safe model | Appropriate if a path cannot be verified from exact definitions and typed audits. | Fail closed rather than accept an unexplained hash. | Not selected for this closed package set. Unknown future packages remain outside this decision. |

## 5. Selected rule: exact ordered migration edges

Retain strict before/after hash validation. Replace the assumption that every
package has an immediately preceding prerequisite-package hash with an explicit,
fully verified path through the permitted intervening L edge.

The fixed structural constraints are A before T, T before E, A before L, and at
most one instance of each migration. Optional packages may be absent, but may not
be skipped as prerequisites. The only complete orders involving L are:

```text
A -> L -> T -> E
A -> T -> L -> E
A -> T -> E -> L
```

Every valid prefix is supported, including A alone and A followed by L. Without
L, the original A -> T -> E order and all its valid prefixes retain their existing
meaning. Other administrative audit events may occur between these schema edges;
they remain fully validated but are not new schema transitions. No edge may be
inferred solely from object presence or a claimed predecessor hash.

For each relevant typed audit, require its existing exact envelope/subject,
canonical/digest integrity, actor/reason/time checks and historical binding scope.
Validate the complete administrative chain, unique action/ID pairing and required
prerequisite order. Preserve each migration's existing current admission checks;
historical scope checks do not replace live migration permission.

### Reconstructing the schema at an edge

1. Observe the actual current object map on the owning reserved connection. Require
   exact recognized complete packages and their reviewed definitions. Distinguish
   original versus lifetime-successor authority SQL exactly. Reject staging,
   unknown objects, partial packages, mixed versions, missing audits and audit-only
   packages. Existing control/isolation validation remains mandatory.
2. For a particular verified edge, reconstruct its before/after maps using only
   the known definition deltas and their validated audit order. Remove T/E sets
   installed later than that boundary. If L occurred later, substitute only its
   exact successor definitions with the original authority definitions; if L
   occurred earlier, retain the successor definitions. At A's before boundary,
   omit A's entire definition set. Preserve every unrelated required definition.
3. Recompute H for both maps. Each audit must match its own before/after hashes,
   not today's default schema or another audit's claimed map. The actual current
   map must equal the endpoint of the verified path. Audit digests alone are never
   enough to authorize an inverse projection.
4. For adjacent schema edges, require preceding installed hash = following
   previous hash. Anchor A in its existing verified claim-package predecessor.
   Thus a post-L attempt may follow A -> L, and a post-L transition may follow
   T -> L, only if all intervening hashes, deltas, scope and ordering verify.
5. Verify L's D0/D1 at L's own audit position, not against a later extended raw
   current map. Later T/E additions cannot change L's stored installed hash or
   excuse a mismatch in the recomputed cutover state.

The current full object set must be checked independently of historical hash
reconstruction. This decision permits no wildcard removal, arbitrary hash list,
caller-defined delta, relaxed SQL matching or general graph of migrations.
Implementations must avoid circular verification in which a historical reader
trusts a digest that is justified only by calling that same reader again.

## 6. Historical packages and reader treatment

All pre-L audit bytes, package IDs, before/after hashes and data rows remain
unchanged. Pre-L T/E edges are checked against original authority definitions at
their own historical boundaries, even when the current authority schema is the
successor. Do not rewrite a package audit to make it fit today's schema.

The existing binaries/readers do not already understand L. As R10 requires, old
code must reject the successor exact schema; it must not silently reinterpret it.
The future compatible readers must distinguish historical edge selection from raw
current inspection:

| Historical consumer | Required selected state |
| --- | --- |
| Authority migration validation / `authority_manifest()` use for S1 | A's actual installation boundary, with any later L/T/E changes reversed only through the verified path. |
| Claim predecessor reconstruction | The original claim boundary, before A; retain its original recorded meaning. |
| Attempt migration validation | T's own before/after boundaries, retaining L if L preceded T. |
| Enrollment-transition migration validation | E's own before/after boundaries, retaining L if L preceded E. |
| L migration validation | L's own before/after boundaries, with later T/E additions removed by verified order. |
| Current schema validation or new installer manifest capture | Actual current raw map; never historical substitution. |

Existing helpers' assumptions that subtracting one package set always finds the
correct historical state must be updated where L can intervene. A stored earlier
audit determines the historical boundary; a caller-supplied exclusion or digest
cannot choose an easier history. Existing plan/source records retain their own
reader contracts; this decision does not rewrite their stored schema references
or authorize a plan to cross an otherwise forbidden transition.

## 7. Post-upgrade packages

For A -> L -> T, T records raw U1 as previous and raw U1+T as installed. Its
prerequisite remains the same exact A package, but the validated connecting path
is A's installed schema -> L's previous schema -> L's installed schema -> T's
previous schema. No original A hash is replaced with U1.

For A -> T -> L -> E, E similarly records the raw upgraded T schema as previous,
and validates T -> L -> E. For A -> L -> T -> E, E follows T directly; T's
installed hash already contains L. For A -> T -> E -> L, all earlier package
audits keep their original hashes, and L validates its cutover after E.

The same T/E migration identity is appropriate because their exact definition
sets and data semantics are unchanged. The combination of package ID, typed audit
position, both computed hashes and verified L edge unambiguously identifies the
schema incarnation. New compatibility is prospective: it allows a future installer
to record its true current hashes, without retroactive rights or audit repair.

## 8. Rollback, failure and restart

| Situation | Required result |
| --- | --- |
| L commits; later package installation fails | Roll back that package's DDL/audit together. L's valid endpoint remains; do not roll back or repair L automatically. |
| Package DDL/audit written; final validation fails | Roll back the complete package transaction. Never commit an edge whose final schema/history checks fail. |
| L rolls back | Its replacement, staging and audit roll back together under R11-A; existing packages retain the original valid lineage. |
| Package existed before L | Preserve its rows and recorded hashes; validate the earlier edge and L independently. |
| Restart between writes in one uncommitted migration | No separately committed lineage record exists. Existing transactional rollback rules apply; no adoption or resumed authority. |
| Commit or cleanup uncertain | Publish no usable success; inspect durable exact schema/audit state read-only. No automatic retry, repair, downgrade or adoption. |
| Audit present without its package, package without its audit, duplicate/reordered edges or unexplained DDL | Reject; never infer a completed edge from partial evidence. |

An original valid prefix is not itself corruption merely because later optional
packages were never installed. A successor schema accompanied by missing/reverted
L evidence is invalid. This preserves existing detectable schema/audit integrity;
it does not introduce protection against privileged replacement of an entire
database by a coherent older snapshot. Existing restore/identity/generation gates
remain authoritative, with no new recovery right.

## 9. Security preservation and prohibited bypasses

Unexpected replacement and unauthorized DDL fail exact current definitions or
recomputed edge hashes. Skipped migrations fail prerequisite/order checks.
Incompatible packages fail the closed ID/definition set. Stale original authority
SQL with a committed L audit fails endpoint verification. Partial rollback fails
schema/audit agreement. Required current row/history/scope checks remain separate.

Explicitly prohibit:

- Accepting arbitrary hashes or accepting old/new hashes without the full verified path.
- Disabling predecessor checks or replacing them with object presence alone.
- Treating a current schema hash as proof of historical compatibility.
- Allowing a package audit to authenticate its own claimed lineage without exact definitions and independently checked prior edges.
- Rewriting old audit rows, inventing missing audits or treating an unknown migration as a harmless intervening edge.
- Using a historical projection for current write admission or weakening `check_control()` / `isolated_admin_control_required`.

Schema lineage is not lifetime-policy adoption, authentication, authority issuance,
writer admission or execution permission. v1/120 seconds remains current/default;
representation of prospective v2/300 seconds grants no production authority.

## 10. Decision A and exact next boundary

**A — POST-UPGRADE LINEAGE CONTRACT COMPLETE.** Select candidate B: the finite,
explicit A/T/E/L transition model using existing typed migration audits and exact
reviewed schema deltas. Preserve raw hash recording, verify every edge, retain
historical package meanings and add no durable lineage format.

**Next boundary: 4e-20-R11-D — post-upgrade schema-package lineage implementation.**
It must implement and focus-test original histories, every permitted L placement
and prefix, later package installation, tampered/missing/duplicate/out-of-order
edges, unexpected DDL, rollback and fail-closed old-code behavior. No implementation
or migration execution is performed or authorized against production by R11-C.

## 11. Validation and explicit production blocks

Only this document is added. Validation is repository inspection, AST parsing of
inspected source surfaces, document whitespace/local links and `git diff --check`.
No pytest, SQL/migration, lifecycle, Z18, T or broad suite. No code/schema/validator
changes, authorities, v2 activation, G1, target mutation, hosted/production access,
permissions, commit or push.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED

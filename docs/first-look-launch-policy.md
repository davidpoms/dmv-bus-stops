# First Look launch policy infrastructure — not activation

`first_look_launch.py` implements an optional reviewed-closed-population guard.
Submission has a disabled enqueue hook; the guard is not connected to a processor
and enables no gate. No schema
changes or production authorization provider are included. Explorer is unchanged.

## Proposed conservative finality

Seal only a qualifying completion at/after an explicitly reviewed inclusive
activation instant and before a separately reviewed exclusive finality frontier.
The frontier is an evidence-review boundary, not an elapsed-time grace period.
An exact full-population inspection must include all competing reviewers,
reconciliation, clock review, identity review and captured immutable evidence.

The guard recomputes that inspection inside the caller-owned writer transaction.
Any difference invalidates the approval, including new competitors, corrections,
backdating or identity changes. Existing validators may reject the change before
the canonical comparison. Even unrelated later completions can invalidate this
conservative full-population approval. A new inspected population and independent
authorization are required; this is not unattended finality.

At/after the frontier, processing stays pending. Validation failures quarantine
the pending record. A matching existing claim is verified and acknowledged;
a conflicting winner requires discrepancy review, never reassignment. Done
retries verify the sealed claim without issuing another. Caller rollback remains
authoritative. No correction or late-discovery policy rewrites an existing claim.

## Required reviewed inputs

`configuration_for(policy)` validates admission configuration only. It does not
authorize capture. The policy has exactly these fields:

- `format`: `first-look-launch-policy-v1`
- `reference`: retained policy review reference
- `activation_at_utc`: explicit canonical UTC instant, no default
- `historical_cutoff_utc`: `2026-09-30T00:00:00Z`
- `historical_qualified_count`: 55 completions, not necessarily 55 claims
- `candidate_artifact_sha256`:
  `c6c2c5d9aa51c24c129bbe1e9f0e24fed735c1e9debdb8afbb8940f27ce94a50`
- `historical_operation_id`: actual sealed historical operation digest
- `historical_qualified_sha256`: canonical digest of its qualified fact list
- `sqlite_utc_provenance`: reviewed reference, or null only when unnecessary
- `gap_assignment_ids`: sorted unique qualifying assignment IDs between the
  historical cutoff and activation
- `gap_review_reference`: review reference, including for an empty interval
- `finality`: `{"mode":"reviewed-closed-population-v1",
  "late_arrivals":"quarantine-and-review","existing_claims":"verify-never-reassign"}`

The supplied candidate artifact hash is a provenance reference, not proof of
certification. The guard neither reads nor changes that artifact. It requires a
real sealed baseline with valid claims, exactly 55 pinned qualifying facts, and
all those facts strictly before the historical cutoff. The actual historical
cohort remains candidate-only until separately reviewed and authorized sealing.

`build_guard(policy, reviewed_population, authorization,
authorization_verifier=...)` additionally requires:

1. An independently inspected `permanent.prepare()` First Look result with an
   exclusive cutoff after activation and an explicit evaluation instant at/after
   that cutoff. This inspection is **not** an instruction to historical-finalize
   the expanded population. Its report includes the complete competitor set.
2. Authorization with exactly `format=first-look-launch-authorization-v1`,
   `reference`, `policy_sha256`, `population_sha256`, and
   `baseline_link_review_reference`. The last reference records independent
   review linking the candidate artifact to the sealed historical baseline.
3. A trusted independent verifier accepting `(authorization, policy_hash,
   population_hash)` and returning exactly `True`. Hashes and self-supplied
   references alone are not approval. No permissive production verifier ships.
   Verification runs at construction and again before each guarded processing.

Missing inputs produce no guard; invalid inputs fail closed. The guard supplies
its immutable admission `configuration`, but never opens a database, selects a
production time, or enables capture/issuance. During processing its reads use the
active transaction and nested read-only report contexts preserve the outer SQL
authorizer. This is a trusted-code validation interface, not a Python sandbox.

## Remaining before application integration

- Independently review and seal the historical baseline and resolve its withheld
  cases; retain the candidate-to-baseline linkage evidence.
- Choose and authorize the activation instant. Review the nine reported completions
  at/after the historical cutoff against that instant. They are not added to the
  historical 55. Gap inventory is not permission to issue gap claims; an unclaimed
  preactivation winner still blocks a live claim for that stop.
- Approve this finality policy, exact population/frontier and reconciliation,
  including clock/backdating/identity exceptions and timestamp provenance.
- Provision an independently reviewed authorization source/verifier and retain
  policy, population and authorization artifacts privately.
- Review deployment schema, activation of transactional admission, separate
  processing, quarantine/retry operations and full-population scan cost.

Existing live operation evidence retains the frozen decision/report/configuration;
the external authorization materials must also be retained. No scheduler, HTTP
integration, production binding, production manifest or automatic gate is added.
Synthetic tests choose test dates and seal test baselines only; they do not
approve a production launch date or certify the real historical cohort.

## Multiple assignments and delivery states

A delivery belongs to an assignment; a permanent claim belongs to a physical
stop. Every qualifying completion at that stop competes, across reviewers, using
the existing parsed completion instant then numeric assignment-ID ordering.
Processing a later delivery may seal the earlier competitor's claim. Neither
assignment creation order nor delivery order grants priority.

Incomplete assignments are retained as exclusions in the reviewed population.
They do not disqualify completed assignments, even at the same physical stop.
If an incomplete assignment later completes, the old closed-population approval
is stale. Before sealing, a newly reviewed population may establish an earlier
winner. After sealing, an earlier competitor requires quarantine/discrepancy
review and can never automatically replace the claim. There is no assumption
that a later-created assignment necessarily has a later completion timestamp.

The existing table is sufficient; no schema migration is added:

| Delivery phase | Persisted representation | Next step |
| --- | --- | --- |
| pending | `state=pending`, no reason | Validate and review finality |
| eligible awaiting finality | pending plus `finality_not_ready` or `reviewed_finality_guard_required` | Obtain independent finality approval |
| sealed | `state=done`, `claim_sealed` or `existing_claim` outcome | Integrity-only idempotent retry |
| quarantined/conflict | `state=quarantined`, bounded reason | Review, then explicit quarantine retry; no reassignment |
| retryable failure | pending plus `retryable_sqlite_lock` | Retry after contention clears |

`delivery_status()` reads this classification; eligibility means qualification
was checked at the last attempt, not that it remains valid or that this delivery
is the winner. A done delivery may acknowledge another assignment's sealed claim.

Unexpected processing errors still roll back and propagate. After rolling back
the failed transaction, a future caller may start a **new** transaction and call
`record_retryable_failure()` for a SQLite BUSY/LOCKED error only. This records a
bounded marker and attempt count without touching evidence or claims. Unknown
errors are not classified as transient. Done/quarantined rows are not reset.
If contention also prevents recording the marker, the original pending record
remains retryable and the caller must retain the failure externally. Caller
rollback also rolls back the marker; no helper opens or commits a transaction.

Synthetic tests model nine completions and three additional incomplete
assignments sharing reviewed stops, using invented IDs. They do not import or
verify production records. No processor or automatic activation is introduced.
The submission enqueue hook remains disabled; see the Phase 1 transaction flow.

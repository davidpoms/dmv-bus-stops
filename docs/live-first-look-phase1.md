# Live First Look: Phase 1 infrastructure only

Review submission now has a disabled-by-default enqueue integration. It does not
seal claims or invoke a processor, startup migration or scheduler. Both existing
`RecognitionGate` flags still default off. No production
configuration or final activation instant is supplied. An unwired guard is now
specified in [First Look launch policy](first-look-launch-policy.md); its policy
and authorization still require independent review. The 55-completion historical cohort before the
exclusive `2026-09-30T00:00:00Z` cutoff remains candidate-only; this release does
not seal it and cannot use candidates as a sealed historical baseline.

## Storage and compatibility

`live_first_look_schema.migrate(database)` rehearses in memory by default;
`apply=True` is explicit migration authorization. It requires the existing
Explorer and permanent-family schemas. It adds only
`recognition_first_look_pending`, keyed by immutable completion assignment ID:

- Immutable configuration JSON/hash binds admission to the activation boundary
  and externally reviewed policy reference/hash, including timestamp provenance.
- Mutable `state` is pending, done, or quarantined; `attempts`, bounded failure
  reason and outcome supply durable retry information.
- Context replacement/deletion and changes after done are prohibited by triggers.
- No leases: the caller's SQLite writer transaction serializes processing.

`qualification.capture_completion()` is the evidence-only portion extracted
from `capture()`. It uses the same qualifier, rule, immutable fact comparison,
sequence and provenance. Existing `capture()` still adds an Explorer job exactly
as before. First Look uses the existing qualification rule `explorer:v1` for
shared completion evidence, but never creates or changes `recognition_jobs`.
This qualification-rule identity is not a First Look award rule.

Existing permanent claim/operation tables retain their schemas and uniqueness.
Live operations have a distinct manifest format and configuration-addressed rule
key. Historical `prepare()`/`finalize()` remain historical-only. Small shared
operation/claim insertion helpers accept the caller's connection; existing claim
integrity reads validate both historical and frozen live-operation evidence.

## Caller-owned submission transaction flow

`submit_review()` preserves the existing evidence commit and derived refresh.
Application configuration defaults `LIVE_FIRST_LOOK_GATE` to `DISABLED` and
`LIVE_FIRST_LOOK_CONFIGURATION` to an empty `Configuration()`. There is no
request or environment-variable activation. Future independently authorized
configuration must supply a capture-only gate and reviewed configuration.

1. Save observations on `observation_conn` and commit as before.
2. Perform derived refresh on `refresh_conn` as before.
3. Update assignment completion in the existing `with refresh_conn` transaction.
4. Only with capture enabled, after a successful one-row UPDATE, call
   `live_first_looks.enqueue(refresh_conn, assignment_id,
   configuration=reviewed_configuration, gate=RecognitionGate(capture=True))`.
5. Commit completion, shared immutable evidence and First Look pending state
   together. Foreign keys are enabled before refresh when capture is enabled.
   On failure, roll back completion/capture, preserving the already committed
   observation and existing saved-evidence retry response. No award is created.

Already-completed submissions retain the existing short-circuit: no enqueue,
refresh or backfill. A retry following enqueue failure reuses saved observations.
SQLite BUSY/LOCKED failures propagate through the same rollback/retry boundary;
there is no new retry loop. Because failed admission leaves no pending delivery,
the processing-stage `record_retryable_failure()` helper is not called here.
It remains available to a future processor for an existing pending delivery.

`Configuration()` supplies no defaults for activation, historical cutoff,
policy reference/hash or naive-timestamp provenance. Explicit enabled admission
requires reviewed configuration. Completions before activation are not enqueued;
activation itself is inclusive. Repeated admission verifies immutable evidence
and the identical configuration; it never resets a processed/quarantined row.

A separately authorized caller would then:

1. `BEGIN IMMEDIATE` with foreign keys enabled.
2. Call `seal_pending(conn, assignment_id, gate=RecognitionGate(issuance=True),
   finality_guard=reviewed_guard)`.
3. Commit the returned pending/done/quarantined result, or roll back on an
   unexpected failure. The primitive never opens a connection or calls BEGIN,
   COMMIT or a full transaction rollback; savepoints make its writes atomic.

No dispatcher is needed for this infrastructure slice. There is no automatic
consumer. Do not use an Explorer job's done state as First Look delivery state.

## Required finality guard; no implicit live policy

The trusted callback `guard(conn, context)` sees immutable trigger evidence,
configuration, ledger sequence and identity digest inside the writer transaction.
SQL writes and transaction control are denied during the callback. This is a
validation contract for trusted code, not a sandbox for arbitrary Python.

Return `None` to defer, or a reviewed decision with exactly:

- `historical_operation_id`: the actually sealed historical First Look operation;
- `evaluation_at_utc`: explicit canonical UTC evaluation instant;
- `inputs`: existing First Look report keyword arguments, including exclusive
  cutoff, complete-population reconciliation and reviewed timestamp provenance;
- `reference`: retained evidence authorizing this finality decision.

The configured policy hash identifies independently reviewed policy material; it
does not authenticate arbitrary callback code. Callback provisioning and approval
remain an operator responsibility. `first_look_launch.build_guard()` supplies a
conservative optional implementation; no callback is selected by the application.

The sealer verifies the historical operation and its persisted claims, cutoff,
all current qualifying competitors and captured evidence, identity history and
the guard's cutoff. It reuses `permanent._prepare()`, `_identity()`, `_ledger()`,
`_candidates()` and claim/fact integrity. These currently scan the full population;
this phase makes no interactive-latency claim. Ordering is always completion UTC
then numeric assignment ID, never queue delivery order. The cutoff must include
the triggering completion; it is not a hard-coded waiting period.

Without a guard or with a deferral, the row stays pending with an incremented
attempt/reason. Known evidence/baseline conflicts quarantine the row; explicit
`retry_quarantined=True` is required to retry it after review. Matching existing
claims are integrity-checked and acknowledged without another claim. Conflicting
claims quarantine with `existing_claim_requires_discrepancy`; they are never
reassigned or deleted. Separately authorized existing append-only discrepancy
handling remains available, not automatically invoked from this transaction.

A new claim, immutable operation and done outcome are atomic. A done retry checks
claim integrity without re-earning from changing source data. Unexpected failures
roll back the savepoint; the caller still owns commit/rollback and recovery.

## Still blocked

- Explicit authorization and migration on the actual deployment target.
- Permanent sealing/reconciliation of the historical baseline, including its
  withheld cases; candidate-only reports are insufficient.
- Final activation instant and review of the interval between historical cutoff
  and activation. Earlier unclaimed winners cannot be relabeled as live claims.
- Reviewed completeness/finality, clock/backdating and late-arrival policy, plus
  its trusted guard implementation and retained decision evidence.
- Explicit production activation and separate processing/failure-handling review.

No production manifests, deployment bindings, automatic gates, UI, Explorer
issuance behavior, assignments or opportunities are changed by this phase.
Tests use synthetic timestamps and cohorts; they do not authorize a real cutoff
or finality policy.

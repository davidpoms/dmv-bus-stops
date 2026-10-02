# Phase 2A global recognition foundation

This is private infrastructure, not a public launch. `RecognitionGate()` defaults
capture and issuance to false. No application endpoint imports or invokes it.
The operator processor has only a read-only planning mode; there is no worker,
scheduler, HTTP backfill, or command-line enable switch. Tests explicitly enable
service gates only on disposable fixture databases.

The seven additive tables retain rules, global scope, completions, jobs, awards,
witnesses and finalized run manifests. No snapshot, route, First Look, consent or
public-event tables are installed. Global-only constraints intentionally reject
unsupported families/scopes; a later approved migration must expand them.
Threshold tier keys are numeric internal identifiers, not public badge names.
Original completion text and timestamp provenance are retained in the ledger.

## Explicit offline migration

After separately authorized backup and rehearsal, use an explicit existing path:

```
python scripts/active/create_recognition_tables.py --db <disposable-copy.db>
python scripts/active/create_recognition_tables.py --db <disposable-copy.db> --apply
```

The default rehearses on an in-memory copy and does not mutate the target.
Apply installs schema and the immutable Explorer v1 definition; it never captures
history or enables services. Missing paths fail instead of creating empty files.
Use the existing reviewer deployment runbook for backup, writer quiescence,
integrity/FK checks and explicit path verification. Keep manifests private.

## Read-only backfill preparation

```
python scripts/active/process_reviewer_recognition.py --db <disposable-copy.db> --rule-key explorer:v1 --through-assignment <approved-cutoff-id> --limit 100
```

Schema must already be installed. The cohort is an explicit assignment-ID upper
bound, not a historical time cutoff. Each manifest gives its continuation cursor;
keep the same approved cohort across batches. Source qualification proposals and
exclusions are separate from candidates, which use only the existing immutable
completion ledger. An empty ledger therefore produces no award candidates.
No source proposal becomes an award in a dry-run. Identical database inputs,
rule and bounds yield identical output, with no wall clock in the manifest.

Naive SQLite-format timestamps are quarantined unless the operator supplies a
reviewed generating-path reference with `--sqlite-utc-provenance`. Merely matching
the SQLite text shape does not establish provenance. Whole-second explicit-offset
timestamps normalize to UTC. Fractional timestamps (even `.000`) are quarantined
pending permanent-inclusion policy; no truncation or observed-time fallback.
Phase 1's fractional timestamp handling remains unchanged.

`capture_batch` is a future gated service boundary, not exposed by the CLI. It
revalidates the reviewed manifest, captures a bounded batch and its final run
atomically, and is restartable/idempotent. It never edits source evidence or issues
awards. It must not be enabled on deployment data without separate authorization.

## Future transaction integration

Preserve evidence commit -> derived refresh -> assignment completion -> recognition
completion/job capture. Only the last two share one short caller-owned transaction.
`capture` does not commit/close its caller, and disabled calls return before SQL.
The existing submission path is deliberately untouched in this phase.

Future processing leases bounded batches in a short `BEGIN IMMEDIATE` transaction,
commits/closes, and calls `prepare_evaluation` on a separate read-only connection.
It materializes the complete history without truncation, the explicit rule and
completion sequence in one read snapshot. That transaction is rolled back and its
connection closed before any candidate sorting, evidence construction or candidate
hashing/serialization. `materialize_ledger` refuses write-capable connections;
`ledger_candidates` accepts only in-memory snapshot inputs. Finalization later
opens a separate short `BEGIN IMMEDIATE` transaction.

Completions carry an immutable, UNIQUE monotonic `ledger_sequence`; an insertion
trigger requires the next sequence, independently of assignment IDs or timestamps.
Finalization checks the indexed maximum sequence, lease ownership/expiry and rule
context rather than recalculating full history. Any intervening completion,
including a late completion with a lower assignment ID, invalidates the prepared
snapshot. Recalculate outside the writer and retry. This intentionally also
invalidates preparation when another reviewer gains a completion; job/award-only
writes do not invalidate it. There is no new table or current-progress projection.

A savepoint protects the complete award/witness/job group. Cross-rule idempotency
compares the threshold, earned instant, numerator and ordered completion witnesses,
excluding presentation labels and rule metadata. Equivalent facts preserve the
original award unchanged. Changed qualifying evidence raises
`award_qualification_evidence_conflict`; the job is not marked done. Failed jobs
remain leased/retryable until a future operator handles the discrepancy or the
lease expires. New evaluation campaigns still need a separately approved job
identity/reconciliation policy. No network or geometry processing belongs here.

Backfill source validation is separate from candidate calculation. The future
capture transaction never generates award candidates; read-only dry-run planning
continues to report ledger candidates separately from proposed source completions.
Dry-run materializes the batch's reviewer histories with one cohort subquery, then
closes its snapshot/connection before calculating candidates. It does not open one
history query per reviewer or construct a large parameter list. A regression uses
an independent fixture UPDATE and COMMIT during CPU calculation, and verifies the
read connection is closed for both preparation and dry-run. Its negative control
confirms that retaining the old read transaction blocks that same COMMIT.

All connection owners roll back and close on failure. Enable FK enforcement on
the actual writer, not just a migration shell. Repository caller inspection found
no callers of `src/review/complete_stop_review.py` outside its own CLI entry point.
The retained helper now enables FKs and explicitly refuses replacement of any
recognition-referenced observation. Its check and mutation share one writer
transaction, preventing a capture/check/delete race. Unreferenced replacement
remains supported; rollback and close are deterministic on failure.

## Retention and rollback

Rules, scopes, completions, awards and witnesses reject UPDATE/DELETE. Jobs have
mutable delivery state but immutable assignment/rule context. Finalized runs
reject UPDATE/DELETE. Foreign keys use NO ACTION. Retain evidence and source rows;
do not copy keys, email, display names, photo URLs or observation narrative into
recognition. No automatic revocation or reassignment is implemented.

Witness completeness is a service-level invariant, not a database sealing claim.
Direct SQL can bypass that invariant. `check_award_integrity(conn, award_id)` detects
missing/extra witnesses, owner or completion-field mismatches, bad evidence hashes,
duplicate stops/assignments, and inconsistent ordering or earned times. It checks
historical frozen facts, not present-day eligibility. Supported finalization checks
both new awards and existing awards before marking the job done. Witness reads are
bounded by the rule threshold plus one (an operational ceiling of 1,000 witnesses;
the approved Explorer rule needs at most 100). No repair or rewrite is performed.

Rollback disables capture/issuance and processing while retaining additive data.
Do not restore an old database over newer contributions. Prove old-code and
maintenance compatibility before activation. Geography certification, route
identity, permanent First Look adjudication, correction policy and public product
decisions remain outside this slice.

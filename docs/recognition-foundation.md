# Phase 2A global recognition foundation

This is private infrastructure, not a public launch. `RecognitionGate()` defaults
capture and issuance to false. No application endpoint imports or invokes it.
The operator processor has only a read-only planning mode; there is no worker,
scheduler, HTTP backfill, or application enable switch. The separate disposable-copy
rehearsal below can explicitly invoke capture-only services; issuance stays disabled.
The separately authorized historical issuance command below can enable issuance
only for the reviewed cohort within that invocation, without enabling capture.

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

`capture_batch` is a gated service boundary, not exposed by the planning CLI. It
revalidates the reviewed manifest, captures a bounded batch and its final run
atomically, and is restartable/idempotent. It never edits source evidence or issues
awards. It must not be enabled on deployment data without separate authorization.

## Controlled disposable-copy capture rehearsal

Populating the immutable completion ledger **is capture**, even on a disposable
copy. `scripts/active/rehearse_recognition_capture.py` is a separate offline tool,
not application activation. Its default is verification-only. It never installs
schema on either file, regenerates the reviewed manifest, leases jobs, or issues awards.
`process_reviewer_recognition.py` remains read-only.

Use an existing initialized working copy, a separate original snapshot, and the
original reviewed planner JSON produced while the ledger was empty. Keep both
databases offline with exclusive operator ownership throughout this operation;
do not run a web app, worker, or another rehearsal against them. SQLite sidecars
and WAL-format files are refused; the tool does not change journal modes or create
WAL/SHM files. Path checks reject source/target aliases and hard links and
the repository/default environment application target, but cannot prove that an
arbitrary path is disposable. The operator must designate it correctly.

Verification-only command (placeholders must be replaced with reviewed values):

```text
python -B scripts/active/rehearse_recognition_capture.py --source-snapshot <snapshot.db> --disposable-target <recognition-working.db> --manifest <reviewed-plan.json> --source-sha256 <verified-backup-sha256> --manifest-sha256 <reviewed-json-file-sha256> --expected-qualified 55 --expected-excluded <reviewed-exclusion-count>
```

Only after separate authorization, adding `--capture-disposable` invokes existing
`capture_batch()` with `RecognitionGate(capture=True, issuance=False)` for that
call only. There is no issuance option. This does not change default gates or
integrate with submission/startup. Never use it on a live/application database.

The wrapper pins the source file and reviewed manifest by SHA-256, compares all
non-recognition application table data/schema between source and target, checks
recognition table definitions and the Explorer v1 definition, and revalidates
source proposals/exclusions using `source_plan()`. Protection-trigger SQL is
derived by running the authoritative installer on an isolated in-memory reference
database, never the source or target. All required triggers must match the exact
stored SQL; unexpected triggers on completions, jobs or runs are rejected before
capture. Even formatting drift requires review. No schema definitions are duplicated.
Application fingerprints use explicit NULL/integer/real/text/blob tags, complete
text (including embedded NULs), complete hex-encoded blobs and exact hexadecimal
float representations. Sorted row hashes make comparison independent of row order.
The provenance reference is preserved, not independently attested by this tool.
Expected exclusions must match the reviewed plan, including unfinished assignments.
The wrapper accepts one complete bounded batch (`has_more=false`, limit <=1,000),
not a partial historical campaign. Cohort bounds are taken from the manifest;
142–210 inclusive corresponds to `after_assignment=141`, not 142.

The target must be empty of operational recognition rows or be an exact prior
capture of this manifest. For 55 qualified records, postchecks require 55 immutable
completions with retained provenance and sequences 1–55, 55 pending unattempted
jobs without leases/errors, one complete backfill run, and zero awards/witnesses.
Application rows and the original snapshot must remain unchanged. Output is a
small JSON verification summary, not private evidence; no report file is written.

Retry the **same original manifest**: its complete canonical JSON determines run
identity. Do not substitute a post-capture plan, whose ledger candidates differ.
Capture itself retains the existing atomic transaction/rollback behavior. Wrapper
postchecks run after the service commits; a postcheck failure is an audit failure,
not an automatic undo. Preserve the disposable copy for investigation; never repair
or rewrite immutable evidence in response. Source SHA is checked on success/failure.
No file-hash check can replace exclusive offline access or detect a change that an
external writer makes and reverses during the check interval.

After successful rehearsal, the existing read-only planner may calculate candidates
from the populated ledger. Those candidates are not issued awards.

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

### One-time historical Explorer issuance

`scripts/active/issue_historical_explorer.py` is a separate, explicitly authorized
operational path for the reviewed assignment 142–210 cohort: 55 already-captured
completions and exactly four Explorer candidates. It never captures, migrates,
changes application configuration, or integrates with HTTP or review submission.
Future automatic recognition remains disabled and requires separate work and
authorization. Populating a completion ledger is capture; this command requires
that capture and its finalized backfill manifest already exist.

Use a maintenance window with application writers and recognition workers stopped.
The command requires standalone rollback-journal databases, distinct snapshot/target
identities, and the existing authoritative recognition schema and protection
triggers. Normal verification/issuance rejects sidecars; recovery has a separate
explicit boundary described below. The snapshot is always opened read-only.

#### Independently reviewed production binding

A path on the issuance command line is not authorization. A separate operator
review must provision `ops/recognition-production-binding.json` at the fixed
repository-relative location. This file is intentionally **not supplied** with
this implementation: no real production target has been inspected or bound.
Missing binding means refusal, including verification. There is no command-line
or environment-variable override of its location and no automatic enrollment.

Review the actual deployment configuration independently to identify the live
database. While writers are stopped, record its resolved absolute path, the
host's `socket.getfqdn()` value, and `Path(database).stat().st_dev` / `.st_ino`.
Review those facts and the approved input hashes separately from execution; do
not generate a binding automatically from whatever `--production-db` was given.
The non-secret binding has exactly these fields (template, not runnable values):

```json
{
  "environment": "production",
  "hostname": "REVIEWED_HOST_FQDN",
  "database": "/REVIEWED/ABSOLUTE/production.db",
  "device": 0,
  "inode": 0,
  "manifest_sha256": "REVIEWED_MANIFEST_FILE_SHA256",
  "snapshot_sha256": "VERIFIED_SNAPSHOT_FILE_SHA256",
  "review_reference": "INDEPENDENT_TARGET_AND_COHORT_APPROVAL_REFERENCE"
}
```

Zero inode is invalid. Restrict changes to this file, the database directory and
the command's code to the authorized operator/deployment account; keep a reviewed
copy in the private operational record. This is an administrative trust boundary,
not protection against an operator who can rewrite the binding or program.
Copies have different filesystem identities; paths and host must also match.
`recognition-working.db` is explicitly forbidden. Replacing/moving the database,
changing hosts or changing input hashes requires a fresh independent binding
review. Do not replace a database file while the command is running.

Verification displays target/environment/host; issuance displays them again
immediately before its authorization boundary. The binding is rechecked for
every job. Tests substitute a synthetic binding in temporary fixtures only.

#### Historical provenance versus live data

The reviewed snapshot hash remains the provenance reference. Only historical
cohort rows are compared to it: complete assignment rows in the manifest,
observations attached to those assignments (including non-community observations),
and their referenced reviewer and physical-stop rows. All columns in those rows
are pinned using lossless type-tagged hashes; private row contents are not logged.
In particular, changes even to a historical owner's profile fields require
review; profile changes for unrelated owners are permitted. Missing/changed rows,
changed timestamps and identity fields, or changed row shape fail closed.
The immutable completions, capture manifest, rule, jobs and all four complete
candidates are separately validated through existing services.

Newer reviews, unrelated profiles, GTFS/application data and unrelated tables do
not need to equal the snapshot. No application rows are restored or overwritten.
Full schema/FK/integrity checks and candidate preparation occur outside writer
transactions. Inside each `BEGIN IMMEDIATE`, a schema-identity check plus bounded
cohort, ledger, job and award checks run immediately before leasing. Unexpected
triggers/schema changes are refused. No whole-application fingerprint or full
integrity/FK scan runs under that writer. The historical row collection has a
1,000-row-per-table safety ceiling; unusually large evidence requires review.

Verification only (replace every placeholder with reviewed values):

```text
python -B scripts/active/issue_historical_explorer.py --production-db /absolute/production.db --source-snapshot /absolute/verified-snapshot.db --manifest /absolute/reviewed-four-candidates.json --manifest-sha256 REVIEWED_MANIFEST_FILE_SHA256 --source-sha256 VERIFIED_SNAPSHOT_FILE_SHA256 --expected-excluded REVIEWED_EXCLUSION_COUNT
```

The manifest is the reviewed post-capture planner JSON, not the original
empty-candidate capture plan. Its non-candidate fields must exactly match the
stored finalized capture manifest. File SHA-256 pins the bytes supplied by the
operator; it is not an approval signature. Independently review and retain those
hashes. Exclusions, provenance, cohort, rule/hash, full candidate evidence and
earned times must match; the command does not regenerate or rewrite the manifest.
Candidate evaluation uses the existing read-only preparation service.

Only after verification, append `--issue-production` to that exact command for
the authorized operation. There is no capture option. The gate is
`RecognitionGate(capture=False, issuance=True)` solely within this invocation.
The existing lease and finalization services process all 55 jobs, including jobs
that produce no awards. Each lease and finalization shares one `BEGIN IMMEDIATE`
transaction: a failed witness/award/job operation rolls back that job and its
attempt. Earlier committed jobs remain committed. This is per-job atomicity,
not an all-cohort transaction.

An unchanged retry accepts only untouched pending/unleased jobs (zero attempts)
or completed/unleased jobs (one attempt) with the exact expected immutable awards
and verified witnesses. Existing leases, unexpected jobs/awards, evidence drift,
or schema drift fail closed. Retry the identical command after an interruption;
do not manually reset jobs or delete awards. A fully completed retry writes
nothing. Unrelated live-data drift does not invalidate a retry. Existing expired
leases are refused rather than reclaimed; investigate them separately. If a lease
created inside this command expires before finalization, the existing service
rejects it and the current transaction rolls back its lease/attempt as well.
No new run records or automatic scheduling are introduced.

#### Hard-interruption recovery

An orderly exception closes the connection and rolls back the current job. A
process kill, host failure or power interruption can instead leave a hot SQLite
rollback journal. Normal verification/issuance refuses it. Keep application and
all other writers stopped. **Never manually delete journals or replace production
with the snapshot.** Retain the database and its journal together if making an
incident copy.

Use the same reviewed arguments as verification, adding `--recover-production`
instead of `--issue-production`. Recovery still requires the production binding,
source hash and reviewed manifest. It explicitly authorizes opening the existing
target through SQLite in read-write mode and reading the schema so SQLite can
perform its own journal recovery. It executes no application DML, migrations,
capture, leases or award issuance. It closes that connection, then uses fresh
read-only connections to check schema, integrity, foreign keys, historical rows,
ledger state and candidates. Recovery and issuance flags are mutually exclusive.
WAL databases/sidecars are unsupported and require a separately reviewed procedure.

After successful recovery, retain the recovery/verification output and run a
separate verification before resuming the identical issuance command. A failed
post-recovery validation does not undo SQLite recovery; investigate the reported
state without resetting jobs. Earlier committed jobs remain committed; the
interrupted job either committed completely or is rolled back by SQLite. An
individual owner's multiple awards and their witnesses share the job transaction,
so a lone incomplete tier/witness collection is corruption, not a retry state.

Successful verification JSON includes the resolved target/environment/host,
binding digest, manifest and snapshot hashes, all four expected candidates
(including full witness identities), expected job count, current awards/jobs,
rule key and integrity results. Issuance additionally reports newly issued awards,
earned UTC timestamps and witness counts. Stderr contains boundary announcements
and a progress event after each committed job. On failure the CLI exits nonzero
and reports current counts/state as **unvalidated**, if readable, or points to the
last committed progress events. An error may follow earlier successful commits;
do not assume it means zero awards. A crash after commit but before output may
also omit the last event; fresh verification is authoritative.

Privately retain the exact reviewed candidate manifest, snapshot manifest and
snapshot/hash, independently approved binding, verification output, recovery
output (if applicable), and issuance stdout **and stderr**. The database retains
immutable award/witness evidence, rule identity and job state, but does not create
a new issuance audit row containing these external file hashes. Output includes
reviewer/witness identities and is not public recognition or consent. Postchecks
are additional reporting, not rollback protection.

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

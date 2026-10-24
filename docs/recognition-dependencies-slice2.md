# Frozen-event dependencies (Slice 2)

This slice adds dependency observation and invalidation to the historical
preparation/event API. It adds no authorization service, signing, execution,
production authority, automatic processing, or startup hook. READY is data, not
permission to write recognition. Existing eligibility and writer code are unchanged.

## Immutable manifest and query boundaries

New preparations store `recognition-dependencies-v1` in their existing immutable
`dependencies` field. It contains the family, exact parent manifest hash, named
query boundaries, observed values, and canonical SHA-256 checksum. The preparation
hash binds this to the frozen event. No new tables or migration are needed.
Revision regenerates both preparation and dependencies; nothing refreshes an
old event in place. Slice 1's five-hash dependency records remain readable but
validation returns INVALID / `dependency_manifest_required`: create a revision,
never backfill the old record silently.

The unit of observation is the existing preparation's actual population and
reconciliation boundary, **not just its winning candidates**:

| Dependency | Boundary and reason |
| --- | --- |
| Assignment inventory | All assignment IDs, including exclusions and newly inserted competitors. First Look's existing reconciliation explicitly inventories every assignment. |
| Review evidence | All assignments' ID, reviewer, stop, status, completion time; all community-review observations' ID, assignment, reviewer, stop and source, including orphans. Geography's existing reconciliation source hash covers this global inventory, not just supplied members. |
| Completion evidence | Complete immutable completion ledger and referenced qualification definitions, as inspected by `permanent._ledger()` and the Geography source reconciliation. |
| Existence | Existence of reviewers/stops referenced by source evidence, plus supplied Geography members. Account profile attributes are not dependencies. |
| Physical identity | Complete events/edges/states, preserving the existing global identity-history review and unattributed-event prerequisite. |
| First Look policy | Permanent family definition, ordering/version, qualification policy; cutoff, provenance, reconciliation references and optional prior-report anomalies remain bound through the full frozen manifest. |
| Geography scope | Exact supplied envelope, identity/version, member list/hash, predicate, provenance, certification assertions, identity review and evaluation/cutoff. Current active status is queried only for supplied members. |
| Geography policy | Permanent definition, approved threshold constants, active predicate; reconciliation source hash and optional prior report remain bound through the manifest. |
| Permanent identities | First Look claims for candidate stops; Geography scope/canonical identities, snapshots, members, awards and witnesses for the supplied scopes. Empty absent private tables are equivalent to installed empty tables. |

This is not a database-wide hash. Reviewer notes/profile edits, non-community
observations, geography discovery labels, and active-status changes outside the
supplied Geography members do not invalidate an event. However, changing actual
review qualification fields outside a Geography scope **does** change its existing
global reconciliation dependency. Excluding that change would weaken current
preparation prerequisites. Likewise a newly inserted excluded assignment changes
First Look's complete inventory. Scoped reconciliation is a future policy/API
decision, not an eligibility change hidden in this implementation.

Historical First Look preparation does not consume live configuration, a live
baseline, gap inventory, or finality frontier. This manifest explicitly excludes
live finality; live operation formats are unsupported. Do not reuse this validator
for a future live event without adding its actual dependencies.

## API and classifications

`dependencies.build(conn, manifest)` runs during preparation under the caller's
transaction. Existing candidate validation remains responsible for current
generation. Archived retrieval checks hashes/linkage without applying today's
threshold mathematics to yesterday's report. Applicable current policy constants
are compared during dependency validation, so a policy version change is STALE,
not accidental archive corruption.

`dependencies.recheck(conn, event_id, current_scope_snapshot=...)` requires an
existing SQLite transaction and returns `{state, reasons}` without writes:

| Result | Reason codes / interpretation |
| --- | --- |
| READY | No reasons: declared dependencies match in this read snapshot, and history is still READY. Not executive approval or a production-readiness verdict. |
| STALE | One or more named `*_changed` reasons: `assignment_inventory`, `review_evidence`, `completions`, `qualification_rules`, `existence`, `identity`, `current_active`, `policy`, `permanent_records`, `scope_snapshot`. `previously_stale` prevents silent restoration even when data later matches. |
| INVALID | Missing/unsupported schema, required identity, community evidence, completion, active status, rule or scope prerequisite; malformed current qualification/active status; invalid identity history; corrupt manifest/report/rule/binding; unsupported boundary/family; target-observation mismatch; detected database corruption. Unexpected malformed event structures return `malformed_event_or_prerequisite`. `previously_invalid` preserves terminal invalidity. |
| VERIFICATION_FAILURE | `transaction_required`, `dependency_read_failed`, or `target_read_failed`. SQLite busy/I/O/other unclassified read errors and filesystem inspection failures do not become durable STALE/INVALID decisions. Raw database errors and private payloads are not returned. |

Removal of an assignment is an inventory change; an extant frozen qualifier
losing its required evidence is INVALID. A valid changed timestamp is STALE;
an unparseable required timestamp is INVALID. An active member becoming inactive
is STALE; absent/ambiguous/malformed active-status evidence is INVALID. Supported
qualification-definition changes are STALE; missing/corrupt/unsupported definitions
are INVALID. No underlying qualification rules are modified.

There is no current external scope registry in this slice. With no replacement
argument, validation checks the retained supplied snapshot and its current local
dependencies. A caller may supply a current replacement envelope for comparison:
a structurally valid change is STALE; missing or invalid certification assertions
are INVALID. This argument is untrusted comparison material, **not authenticated
certification or a claim that the latest external snapshot was discovered**.
Scope completeness and authentic provenance still require independent evidence.

`recording_subject(event_id, result)` describes the existing exact state-history
persistence approval. After obtaining that existing disposable approval,
`record_validation(conn, event_id, expected, authorization=..., authority=...)`
acquires the writer lock, reruns validation, and requires exact equality with the
expected result before calling `events.record_event_state()`. A changed result
raises `validation_result_changed`; READY and VERIFICATION_FAILURE cannot be
recorded as invalidations. Concurrent duplicate attempts cannot append conflicting
decisions. Already recorded states are never restored. Corrupt event/schema/history
may be reported INVALID but cannot be persisted through an untrustworthy history;
the caller must retain that result for a future controlled workflow.

## Concurrency, trust and remaining boundaries

Read-only validation describes one SQLite snapshot. Under WAL a concurrent writer
can commit while a reader still correctly sees READY in its old snapshot. The
tests demonstrate this limitation. State recording serializes its recheck and
append within the caller's writer transaction and uses savepoint rollback; it does
not commit. It does **not** close the future validation-to-authorization-to-commit
race. A future coordinator must establish and enforce that linearization boundary.

The observed hostname/path/device/inode is not production enrollment. There is no
enrollment registry to validate, no authenticated deployment or preparer, no trusted
clock, and no approval lifecycle here. Hashes are integrity checks, not signatures
against a privileged administrator who rewrites all data and hashes. Code-level
qualification changes require a deliberate rule/deployment version boundary;
these fingerprints cannot detect unversioned arbitrary Python changes. Production
provisioning remains unavailable, and neither event state nor validation results
can satisfy an existing writer's Authorization + opaque Authority requirement.

# Read-only Geography Steward inspection

This report evaluates coverage against supplied scope snapshots. It does not
certify geography, publish snapshots, install schema, capture completions, issue
awards/claims, or change Explorer, First Look, progress, assignments or UI.
Use only an explicitly authorized offline SQLite copy. No CLI, HTTP route or
automatic recognition integration is introduced.

## Python interface

```python
from src.review.recognition.geography import build_geography_report
from src.review.recognition.rules import canonical

report = build_geography_report(
    database="/absolute/path/to/authorized-offline-copy.db",
    scope_snapshot=reviewed_snapshot,  # JSON object described below
    cutoff_utc=reviewed_cutoff,       # exclusive YYYY-MM-DDTHH:MM:SSZ
    sqlite_utc_provenance=None,      # reviewed reference only, never invented
    reconciliation=None,
    previous_report=None,
    thresholds=None,
)
print(canonical(report))
```

The caller is responsible for private artifact retention. Output includes internal
reviewer, stop, assignment and observation IDs. `report_sha256` is the canonical
SHA-256 of all report fields except itself, not the hash of formatted file bytes.
There is no clock-dependent generation time. Repeated identical inputs produce
identical reports. Cutoffs must be explicit whole-second UTC ending in `Z`;
fractional timestamps follow permanent qualification's rejection policy.

## Explicit scope snapshot input

The envelope is:

```python
body = {"format": "geography-scope-snapshot-v1", "scopes": [scope, ...]}
snapshot = {**body, "snapshot_sha256": digest(body)}
```

Each scope requires:

| Field | Meaning |
| --- | --- |
| `dimension` | `dc_anc`, `dc_ward`, `municipality`, `county`, `state`, or explicitly certified `census_place` |
| `canonical_geography_id` | Namespace-qualified stable identity; not an ambiguous display name |
| `scope_key` | Stable recognition scope identity |
| `scope_version` | Reviewed boundary/scope version |
| `captured_at_utc`, `effective_at_utc` | Whole-second UTC timestamps no later than the evaluation cutoff |
| `source_provenance` | Object with nonblank `reference` and 64-character SHA-256 `sha256` for the retained source artifact |
| `boundary_provenance` | Same structure, identifying retained boundary provenance |
| `certification` | Object with `approved: true` and a nonblank independent review `reference` |
| `active_membership_predicate` | Exactly `stop_gtfs_status.current_gtfs = 1` |
| `members` | Exact population entries, each `{physical_stop_id: integer, current_gtfs: integer}` |
| `membership_sha256` | `digest(members)` using the supplied list order |

Use `digest` from `src.review.recognition.rules`. Hashes detect input changes;
they do not prove the referenced artifacts or certification exist. The report
does not open referenced paths, fetch URLs, or invent certification. Retain and
review the actual source/boundary artifacts separately. An operator must not
turn current labels into "certified" snapshots by merely filling these fields.

Missing/malformed scope metadata, hash mismatches, duplicate scope identities,
contradictory member statuses, unknown physical identities, or absent certification
produce unresolved scope results. Duplicate identical member entries never
increase the denominator. Only an integer `current_gtfs` equal to 1 counts;
strings and booleans are invalid member input, and other integers do not count.

Current `stop_jurisdiction` values are reported separately as discovered
candidate labels across independent dimensions, with ward normalization and
state/county context. They are **never** substituted for the supplied membership.
Municipality labels do not automatically establish Census place identity.
Null geography, missing boundary versions and ambiguous identity remain audit
work; discovery does not certify any scope, including the five progress scopes.

## Evidence and calculations

One `mode=ro`, `query_only` read transaction materializes source, immutable ledger,
identity and current discovery inputs. All reviewers are evaluated independently.
Existing permanent `qualify()` validation and immutable rule loading are reused;
current progress and amenity/inventory data are not qualification inputs.

Ledger completions must still agree with qualification-relevant source evidence.
Stored reviewed SQLite UTC provenance is reused when available. Source-only
qualifying facts appear under `uncaptured_evidence`, never in ledger-backed N.
Missing ledger tables, orphan evidence, changed source identities/timestamps or
invalid qualifying evidence are surfaced, not repaired. Recognition schema need
not be installed to inspect uncaptured evidence.

D is the distinct active member population in the supplied snapshot. N is the
distinct intersection with a reviewer's validated ledger completions strictly
before the cutoff. Witnesses select the earliest qualifying completion per stop,
ordered by normalized completion instant then numeric assignment ID. Repeated
reviews do not increase N. Uncaptured/rejected facts remain visible separately.

Default report thresholds match the design:

- D < 10: ineligible.
- D = 10–99: 25/50/75/100%, requiring `max(5, ceil(D*p/100))`.
- D >= 100: 10/25/50/75%, requiring `max(10, ceil(D*p/100))`.

`thresholds` optionally replaces the complete `DEFAULT_THRESHOLDS` dictionary
for explicit report-only comparisons. The report retains it and its hash and
states whether it uses design thresholds. This creates no permanent rule or tier
identity. `candidate_tiers` are percentage/required-count calculations, not awards.

Each reviewer/scope includes D, N, required counts, candidate tiers, counted IDs,
witnesses, exclusions, uncaptured evidence and quality blockers. `coverage_satisfied`
is null when unresolved, otherwise a boolean indicating at least one reached
threshold. Candidate arithmetic remains visible for inspection even when blocked.
`issuance_ready` is **always false**, including when coverage is satisfied:
trigger/earned-date policy, lifetime tier identity and permanent geography
infrastructure are outside this implementation.

## Reconciliation, changes and limitations

Optional `reconciliation` requires exactly `reference` and `source_sha256` from a
prior inspected report. A matching hash binds the assertion to source assignments,
community observations and ledger facts (plus orphan evidence). It does not
prove historical completeness; independent review is necessary. Missing or
mismatched reconciliation remains a blocker. Snapshot/identity checks are separate.

`previous_report` must have a valid canonical checksum and matching report format.
Comparison flags source, identity history, cutoff, thresholds, scope metadata,
membership, denominator changes and scope removals. Denominator shrinkage is
explicit. A follow-up report does not silently resolve previously flagged changes.

Identity edges and non-current identity states flag affected populations. Events
without attributable edges are a conservative global blocker, as is incomplete
identity history. No predecessor credit is transferred to successor identities.
These exceptions require review rather than automatic split/merge allocation.

Current database inactivity does not override a supplied historical snapshot.
Conversely, inactive-at-snapshot members are excluded. The report neither reads
nor revokes existing awards. It never assigns an earned date, backdates historical
geography from current membership, or awards because a denominator shrank.

Initial production scopes, boundary quality tolerances, snapshot publication,
historical attribution, catch-up policy and issuance remain unresolved operational
or product decisions. This module enables inspection, not permanent recognition.

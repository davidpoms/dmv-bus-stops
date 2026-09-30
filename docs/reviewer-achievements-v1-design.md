# Reviewer achievements and community recognition: proposed V1

Status: design for review, not an implemented feature or approved migration.
Repository baseline: `ad25557`. Prepared September 30, 2026.
This work changes documentation only. No application, schema, migration, test,
or database changes are authorized by this document.

## Product contract

Achievements are permanent accomplishments. Leaderboards describe changing
community activity using separately named metrics, never a combined points
score. Public recognition requires explicit consent, defaults off, and can be
withdrawn without deleting private achievements. A display name is not consent.
V1 uses the existing reviewer display name when current public consent permits
it. Private progress, achievements, First Looks, geography progress, next
milestones and eventual certified route progress never require public opt-in.

An active stop is **exactly** a physical stop with
`stop_gtfs_status.current_gtfs = 1`. All counting uses distinct canonical
`physical_stop_id` values, not bus-stop members, observations, assignments, or
GTFS stop IDs. Historical achievements survive subsequent stop inactivity.
Identity splits/merges must not multiply historical credit automatically; retain
the original physical identity and evidence and consult the existing identity
lineage when explaining it.

Achievements do not change review eligibility, assignment routing, immutable
observations/photos, consensus, serving directions, geography presentation, or
SQLite connection lifecycle. WMATA shelter/bench inventory remains
non-authoritative current amenity evidence. No amenity-presence answer earns
more recognition than another; recording an unknown answer can be legitimate.

The architecture remains a proposal. Selected V1 product directions below are
distinct from explicitly provisional thresholds and launch prerequisites.
Disabled or unresolved families must not silently award under invented defaults.

## A. Current implementation and evidence

| Existing area | Relevant implementation | Consequence for this design |
| --- | --- | --- |
| Reviewer identity and authentication | `src/review/assignment_router.py::get_or_create_reviewer`; `src/api/app.py` sign-in, verification, status, profile endpoints; `scripts/active/create_review_tables.py` | `community_reviewers` stores private keys, email and display name, but no recognition consent. New public projections must be independent of the existing private profile response. |
| Assignments | `stop_review_assignments`: `id`, `stop_id`, `reviewer_id`, `status`, `created_at`, `completed_at`, scenario/campaign | Completed status alone is insufficient; require a matching community observation. Existing assignment columns do not enforce all these relationships with foreign keys. |
| Observations and photos | `stop_observations`; `src/review/attachments.py`; `/review/submit` | Observations carry physical identity, source, reviewer and assignment. `idx_stop_observations_assignment` is nonunique; qualification must detect ambiguity, not assume uniqueness. Photo attachments remain immutable URL references and are never server-fetched. |
| Submission completion | `src/api/app.py::submit_review` | Evidence commits before consensus/derived refresh. Completion is set afterward with `completed_at=COALESCE(completed_at,CURRENT_TIMESTAMP)`. Failed refresh leaves saved evidence retryable; matching retries do not replace it. Eligibility starts at validated completion, not evidence insertion. |
| Consensus | `src/review/consensus.py::calculate_stop_consensus` | No immutable independent-voter transition ledger suitable for Consensus Builder. Defer it. |
| Current network | `physical_stops`, `physical_stop_members`, `stop_gtfs_status`; identity event/edge tables in `src/database/schema.sql` | Current progress and permanent award evidence are different datasets. Preserve identity history. |
| Geography | `stop_jurisdiction`; `src/amenities/status_synthesis.py::canonical_dc_ward` and `geography_status_rows`; `/pipeline/geography` | Reuse canonical ward semantics; dimensions remain independent. Current string membership is not a historical boundary snapshot. |
| Routes | `routes`, `stop_routes`, `gtfs_stop_map`; `src/ingestion/load_gtfs.py::save_routes` / `save_stop_routes`; `scripts/active/rebuild_stop_routes_clean.py` | `save_routes` stores short names in globally unique `routes.route_id`, losing certified agency/native route identity. Permanent route awards are blocked. |
| Profile | `/reviewer/profile`, `/api/reviewer/profile`; `src/dashboard/templates/reviewer_profile.html` | Profile rendering currently includes inline JavaScript, activity and stewarded stops. There is no existing `static/reviewer_profile.js`. GET profile may create a reviewer through `get_or_create_reviewer`; new recognition reads should not do so. |
| Dashboard | `src/dashboard/templates/dashboard.html`, `src/dashboard/static/dashboard.js`, `dashboard.css` | Existing `communityProfileCard` is initially hidden and includes `communityProfileName`. Adapt this integration point and add a visible generic progress callout; retain map/network priority and the sticky jurisdiction table. |
| Review completion UI | `src/dashboard/templates/review.html`; `src/dashboard/static/safe_render.js` | Any later achievement notice must be separate from successful review submission and use safe DOM rendering. The existing response's `first_review` count is not the proposed durable First Look adjudication. |
| Operations | `docs/reviewer-deployment-runbook.md`, `docs/sqlite-lifecycle-hotfix.md` | Explicit database path, offline migration, deterministic close/rollback and short transactions remain requirements. No request-time DDL, WAL/timeout workaround, or application-startup backfill. |

The preceding read-only feasibility analysis used a local snapshot with 8,306
physical stops, 7,117 active stops, five reviewers and **zero completed
assignments/observations**. These are not production pilot totals or evidence
that historical production reviews are ineligible. Its scratch report is not a
release artifact. Reproduce network and qualification checks against an
authorized deployment snapshot before implementing/backfilling.

That snapshot had 128 provisional route groups, 125 with at least ten mapped
active physical stops. Of 11,162 retained GTFS stop/route pairs, 51 were unmapped;
member joins reduced to 10,614 distinct physical-stop/route pairs. These counts
illustrate mapping loss and duplicate-member risks, not certified route coverage.

### Anonymized production pilot calibration (September 30, 2026)

A later read-only production analysis, supplied in the final product review,
found 55 observations, 55 distinct reviewed physical stops and 55 completed
assignments. All 55 observations linked to valid completed assignments; zero
lacked a valid completed assignment. Four reviewers contributed, with anonymized
distinct-stop totals of 42, 7, 5 and 1. Observations ranged from September 23
through September 29, 2026. Because all 55 reviewed physical stops were distinct
at that snapshot, all 55 also fall into the proposed First Look winner population.

These findings are threshold/product calibration evidence, not an already-created
award ledger or authorization to mutate/backfill production. They are separate
from the earlier local snapshot with no completed-review history. This document
refinement did not access production or independently rerun the supplied analysis.

| Anonymized contributor | Recorded contribution concentration | Progress under selected geography rules |
| --- | --- | --- |
| 42 reviews | Arlington municipality: 42/473 = 8.9% | First 10% milestone requires 48 stops: 42/48. |
| 7 reviews | ANC 1D: 4/26 = 15.4%; Ward 1: 7/153 = 4.6% | ANC's first 25% milestone requires 7 stops: 4/7. |
| 5 reviews | ANC 6D: 5/38 = 13.2%; Ward 6: 5/197 = 2.5% | ANC's first 25% milestone requires 10 stops: 5/10. |

These examples support showing localized geography progress even with relatively
few total reviews. They describe where recorded contributions were concentrated,
not where reviewers live. They are progress examples, not retroactively approved
permanent awards; geography quality certification still applies.

**Provisional route calibration: NON-CERTIFIED.** The strongest observed coverage
was A76 at 23/88 = 26.1%; the same contributor's next strongest was F62 at
12/108 = 11.1%. Anonymized provisional route-touch totals were 9, 8, 3 and 2;
using the >=3 distinct reviewed-stop qualifying-route concept, inspected counts
were 6, 2, 1 and 0. Simple route-touch counting is too permissive because one
physical stop can serve multiple routes. The >=3-stop definition better represents
meaningful route breadth. This pilot produced a natural first 25% Route Coverage
crossing without a cluster of near-identical 25% crossings for that reviewer.
Neither A76, F62 nor any current `routes.route_id` value is certified permanent
route identity. These observations do not authorize route awards.

## Qualification, counting and permanent evidence

A qualifying completion must join an observation with `source='community_review'` to
an assignment with `status='completed'`, matching `assignment_id`, reviewer ID,
and observation physical stop = assignment `stop_id`. It needs a usable
completion timestamp and existing reviewer/physical identity. This source
literal matches `submit_review` and the current community-observation queries.
Exactly one eligible observation must be resolved per assignment: quarantine
conflicting duplicates rather than pick whichever row a query returns. Repeated
reviews of one physical stop never increase distinct-stop credit.

Qualification does not require the stop still be active. That is essential for
historical Explorer and First Look credit. Current coverage adds an explicit
intersection with the active population and qualified membership snapshot.
Imported/legacy observations without a matching completed assignment receive no
invented completion, reviewer identity, or attribution.

| Family | Selected direction or explicitly unresolved calculation | Permanent record / launch gate |
| --- | --- | --- |
| Explorer | Selected: distinct qualifying physical stops ever reviewed; milestones 5/20/50/100 | Earliest qualifying completion per stop; freeze the threshold witness set. Historical credit survives inactivity. Final tier display names may remain open. |
| Geography stewardship (`geography_steward`) | Selected size-band calculation: for one geography scope, D is current active distinct members and N is historical distinct reviewed stops intersected with those members. D<10 is ineligible. For D=10–99, tiers 25/50/75/100%, required `max(5, ceil(D*p/100))`. For D>=100, tiers 10/25/50/75%, required `max(10, ceil(D*p/100))`. | Freeze scope/boundary version, D, N, member population and review witnesses. Quality certification, stable identity/provenance and membership-change behavior remain prerequisites/decisions, not uncertainty about the selected calculation. |
| Regional Explorer | Count distinct geography values within one chosen dimension only; never add wards to ANCs/counties/municipalities | Thresholds and minimum meaningful contribution per geography unresolved. Block awarding until these and historical/current membership semantics are approved. |
| First Look | First qualifying completion at a physical stop ordered by parsed completion instant, then numeric assignment ID | One permanent winner per physical identity. Freeze winning observation/assignment and ordering version. Cumulative milestone thresholds/names unresolved. |
| Route Coverage | Selected ladder: 25/50/75/100%, ceiling rounding, on one certified agency-qualified stable route. Candidate eligibility floor: D>=10 active mapped distinct physical stops. | BLOCKED from permanent implementation/awarding until stable route identity and mapping-quality certification exist. Freeze stable route/version, full denominator, numerator, witnesses and rule version. Label mapped-stop coverage honestly. |
| Route Connector | Selected qualifying-route definition: >=3 distinct qualifying reviewed physical stops on that stable route. Candidate milestones: 3/5/10/20 qualifying routes. | Milestone ladder remains provisional; the >=3-stop definition is selected and replaces route-touch semantics. Stable route identity and frozen per-route evidence required. Historical/current membership attribution remains open. |

Use one neutral internal family/rule identity, `geography_steward`, across
geography dimensions. Display titles are presentation only:

- ANC or genuinely neighborhood-scale scope: **Neighborhood Steward — ANC 6D**.
- Ward: **Ward Steward — Ward 6**.
- Municipality: **Community Steward — Arlington**.
- County: **County Steward — Montgomery County**.

These titles must not create separate calculation systems or duplicate awards
for the same family/scope/tier. Never combine ANC, ward, municipality and county
into one coverage value or impose a universal hierarchy. Edge-case vocabulary
remains open; the selected size-band mathematics does not.

For example, a geography with D=13 requires 5, 7, 10, 13 reviews, and D=100
requires 10, 25, 50, 75. Crossing the size-band boundary can change current
targets; prior awards are never reduced. Proposed tier identity is ordinal
(`tier_1` through `tier_4`), with the actual percentage/band frozen per award.
Product must approve this interpretation rather than allowing network changes
to silently create a different set of percentage-named awards.

Coverage progress can change without a new review when the network changes.
Proposed V1 policy: award on a qualifying completion evaluated against a
published snapshot, not simply because a denominator shrank. Show current
progress separately, and label its snapshot date. Whether a network publication
alone may trigger an award remains a product decision. Do not backdate an award
to a historical completion using today's denominator.

Defer Consensus Builder until independent-voter eligibility and atomic
consensus-transition evidence exist; Photo Contributor until moderation and
usefulness criteria exist; and scarce Jurisdiction Pioneer unless separately
approved. Do not create speculative award rows for these families.

## B. Proposed schema additions (specification only)

The following is an exact proposed relational shape for review, not executable
migration SQL. All tables are new; existing application tables/columns remain
unchanged. `I` means INTEGER, `T` TEXT. All columns are NOT NULL unless suffixed
`?`. PK, FK, UQ and CHECK describe required migration constraints. Boolean
integers have `CHECK IN (0,1)`. Canonical timestamps are fixed-width UTC RFC3339
text with second precision, e.g. `2026-09-30T15:00:00Z`; parse legacy timestamps
before inserting, never lexically mix formats. JSON text is validated by the
service and migration checks without assuming a SQLite JSON extension.

Foreign keys use NO ACTION (no cascading deletion of historical credit).
Connections must enable existing required FK enforcement. Existing physical
stop IDs reference `physical_stops(id)`; reviewer IDs reference
`community_reviewers(id)`. Service checks enforce cross-table semantic matches
that a simple FK cannot establish. Proposed immutable tables are append-only
through the service; migration-installed UPDATE/DELETE rejection triggers on
rules, snapshots, memberships, completions, claims, awards and witnesses should
enforce that contract. Operational job/settings rows are deliberately mutable.
Implement and test those triggers only in the later approved migration.

| Proposed table | Columns and constraints |
| --- | --- |
| `recognition_rule_versions` | `rule_key T PK`, `family T`, `version I CHECK>0`, `definition_json T`, `definition_sha256 T`, `created_at_utc T`; UQ(family,version). Store thresholds, qualification/timezone policy and algorithm version; activation is deployment configuration, not editing this row. |
| `recognition_preferences` | `reviewer_id I PK FK`, `public_id T UQ`, `public_enabled I DEFAULT 0`, `consent_version T?`, `updated_at_utc T`; random unguessable public ID, never a reviewer key or numeric ID. CHECK enabled implies nonempty consent version. No separate alias column: resolve current `community_reviewers.display_name` only with current consent; service validates an allowed display name before enabling, and public rendering suppresses a missing/invalid name without falling back to email. |
| `recognition_consent_events` | `id I PK`, `reviewer_id I FK`, `public_enabled I`, `consent_version T`, `recorded_at_utc T`; private append-only record of explicit changes. Display-name edits do not enable recognition. |
| `recognition_scopes` | `scope_key T PK`, `kind T CHECK IN ('global','geography','route')`, `dimension T?`, `canonical_key T`, `label T`; UQ(kind,dimension,canonical_key) for non-global scopes; reserve exactly `scope_key='global'` for global awards. Geography keys include a namespace/stable boundary identifier, never bare ambiguous city names. Route key embeds stable route ID. |
| `recognition_snapshots` | `snapshot_id T PK`, `captured_at_utc T`, `manifest_json T`, `manifest_sha256 T UQ`, `qualification_rule_key T FK recognition_rule_versions`; represents an immutable, fully validated published network snapshot. Manifest records source/feed/boundary hashes and quality audit. Failed drafts never enter published tables. |
| `recognition_snapshot_scopes` | `snapshot_id T FK`, `scope_key T FK`, `scope_version T`, `eligible I`, `quality_json T`; PK(snapshot_id,scope_key). Route scope_version identifies certified route version; geography version identifies boundary/source version. Ineligible scopes have explicit reasons. |
| `recognition_snapshot_members` | `snapshot_id T`, `scope_key T`, `physical_stop_id I FK`; PK(all three); composite FK(snapshot_id,scope_key) to snapshot_scopes. Members contain only `current_gtfs=1` stops at capture. A global scope retains the entire active population. |
| `recognition_completions` | `assignment_id I PK FK stop_review_assignments(id)`, `observation_id I UQ FK stop_observations(id)`, `reviewer_id I FK`, `physical_stop_id I FK`, `completed_at_utc T`, `qualification_rule_key T FK`, `origin T CHECK IN ('live','backfill')`, `recorded_at_utc T`; immutable validated completion fact, not an award. |
| `recognition_jobs` | `assignment_id I PK FK recognition_completions`, `snapshot_id T? FK`, `state T CHECK IN ('pending','leased','done','quarantined') DEFAULT 'pending'`, `lease_token T?`, `lease_until_utc T?`, `attempts I DEFAULT 0 CHECK>=0`, `last_error_code T?`, `updated_at_utc T`; bounded diagnostic codes, not private payloads. Live network evaluation pins a published snapshot; null means global-only or pending prerequisite. |
| `recognition_first_looks` | `physical_stop_id I PK FK`, `assignment_id I UQ FK recognition_completions`, `rule_key T FK`, `decided_at_utc T`; reviewer, observation and completion time are obtained from the immutable completion FK. Store no competing winner. |
| `recognition_awards` | `award_id T PK`, `reviewer_id I FK`, `family T`, `scope_key T FK`, `tier_key T`, `rule_key T FK`, `snapshot_id T? FK`, `earned_at_utc T`, `evaluated_at_utc T`, `origin T CHECK IN ('live','backfill')`, `numerator I CHECK>=0`, `denominator I? CHECK>0`, `evidence_sha256 T`, `evidence_json T`; UQ(reviewer_id,family,scope_key,tier_key), deliberately independent of rule version. Network families require snapshot and applicable scope version in evidence. |
| `recognition_award_witnesses` | `award_id T FK`, `assignment_id I FK recognition_completions`; PK(both). Evidence JSON specifies counted physical IDs, per-scope attribution and rule calculation; witnesses plus retained snapshot members make the hash verifiable, not merely decorative. |
| `recognition_activity_events` | `event_id T PK`, `award_id T UQ FK`, `publish_after_utc T`, `public_month T`, `template_key T`; immutable milestone event with no copied display name/consent. Public rendering always joins current preference and allowed display name. Delay/month projection remains proposed pending public activity privacy decisions. First Look claims need not each produce a feed item. |
| `recognition_runs` | `run_id T PK`, `kind T CHECK IN ('backfill','evaluation','snapshot')`, `started_at_utc T`, `finished_at_utc T?`, `manifest_json T`, `state T`, `summary_json T?`; private operator audit including cutoff, code/rule versions, counts and quarantines; mutable until finalized. |

Required indexes, in addition to PK/UQ indexes:

- completions `(reviewer_id, physical_stop_id, completed_at_utc, assignment_id)`;
  `(completed_at_utc, assignment_id)`; and
  `(physical_stop_id, completed_at_utc, assignment_id)`;
- jobs `(state, lease_until_utc, assignment_id)`;
- snapshot members `(snapshot_id, physical_stop_id, scope_key)`;
- awards `(reviewer_id, earned_at_utc, award_id)`;
- activity `(publish_after_utc, event_id)`;
- consent events `(reviewer_id, recorded_at_utc, id)`.

Route prerequisite additions, introduced in a separate phase:

| Proposed table | Columns and constraints |
| --- | --- |
| `recognition_agencies` | `agency_key T PK`, `name T`, `namespace_provenance_json T`; agency_key is a curated namespace, not assumed equal to a feed-local agency_id. |
| `recognition_routes` | `stable_route_id T PK`, `agency_key T FK`, `created_at_utc T`; opaque stable identity, not a short name. |
| `recognition_route_versions` | `route_version_id T PK`, `stable_route_id T FK`, `feed_sha256 T`, `native_agency_id T`, `native_route_id T`, `short_name T?`, `long_name T?`, `effective_from_utc T`, `effective_until_utc T?`, `provenance_json T`; UQ(feed_sha256,native_agency_id,native_route_id); CHECK until>from when present. Certification rejects conflicting/overlapping identities. |
| `recognition_route_stop_provenance` | `route_version_id T FK`, `gtfs_stop_id T`, `physical_stop_id I FK`, `mapping_method T`, `mapping_evidence_json T`; PK(route_version_id,gtfs_stop_id,physical_stop_id). Certification detects ambiguous mappings; multiple GTFS members may legitimately collapse to one physical stop. |
| `recognition_legacy_route_crosswalk` | `legacy_route_row_id I FK routes(id)`, `route_version_id T FK`, `evidence_json T`; PK(both). One-to-many ambiguity is recorded for audit, never automatically accepted as certified attribution. |

Schema size is intentional separation of private eligibility, immutable evidence,
mutable delivery state and public consent. Implement only tables required by an
approved phase; no route tables or placeholder awards are needed for Explorer.
The migration implementation must supply concrete DDL, FK-ordering, trigger and
round-trip tests; this document itself is not a schema installation mechanism.

## C. Proposed service boundaries

Proposed new modules (none exist as a result of this task):

- `src/review/recognition/qualification.py`: strict join validation, timestamp
  parsing, duplicate quarantine and immutable completion recording.
- `rules.py`: pure versioned calculations over explicit evidence sets; no Flask,
  database opening, profile mutation, or hidden current-time reads.
- `snapshots.py`: offline snapshot validation/publication, independent geography
  scopes and eventually certified route provenance. Reuse existing ward
  normalization instead of creating competing semantics.
- `awards.py`: transactional uniqueness, First Look adjudication, evidence and
  milestone event insertion. Accept caller-owned connections explicitly.
- `progress.py`: bounded read-only private projections and useful next targets;
  separate current progress from permanent awards; never gate either on public
  recognition consent.
- `community.py`: strict public field allowlists, live consent filtering,
  metric-specific rankings and delayed milestone summaries.
- An explicit operator command, proposed
  `scripts/active/process_reviewer_recognition.py`, handles bounded job batches
  and reconciliation. An offline migration/backfill command is separately
  reviewed. No worker/thread launches from Flask import or GET handlers.

Start with an operator-run batch processor and observable backlog. Scheduling a
recurring job is a later explicit deployment step, not an assumption about
PythonAnywhere capabilities. Evaluation failures leave pending work and must
not change already completed reviews. No network calls or scientific/geospatial
index construction belongs in these services' interactive paths.

## D. Proposed API contracts and calendar semantics

All new routes below are proposals. GET handlers are read-only, consume cursors
before closing, use bounded queries, and never create reviewer accounts, schema,
snapshots or awards. Private identity comes only from the authenticated session
and matching reviewer key; reject supplied reviewer IDs as authority. Proposed
initial private recognition access requires verified sign-in; treatment of
anonymous pilot sessions is an explicit product decision.
Owner authentication is distinct from public consent: private progress remains
available with `public_enabled=0` or no preferences row. A preferences row is not
created by a progress GET.

| Endpoint | Proposed contract |
| --- | --- |
| `GET /api/reviewer/progress` | 401 without owner authentication. Return `as_of`, `processing_pending`, `explorer:{count,next_threshold}`, `first_looks:{count,next_threshold}`, bounded `coverage` rows with dimension/scope, numerator/denominator, required count, eligibility/quality reason and snapshot date; `awards` with award code, label, private earned date and evidence explanation; bounded `next_targets`; `public_recognition_enabled`. Null next threshold means unresolved/exhausted, not zero. Pagination for awards. |
| `POST /api/reviewer/recognition-preferences` | Owner authentication plus CSRF; explicit boolean `public_enabled` and `consent_version`. Enabling requires prior disclosure that the existing display name may appear on leaderboards and community achievement activity; validate the current account display name, with no alias parameter. 400 invalid payload/CSRF, 401 unauthenticated, 403 mismatched ownership. Persist settings and consent audit atomically. Return only updated settings. Display-name changes use the existing profile API and never toggle consent. |
| `GET /api/community/leaderboard?metric=distinct_stops&period=all_time` | Public top-N, capped server-side; allowlisted metrics/periods, 400 otherwise. Return metric definition, timezone, period boundaries, `as_of`, and rows `{rank,public_id,display_name,value}`. Resolve the current allowed display name only under current consent. No private IDs, emails, reviewer keys, exact review times/coordinates, stop lists or raw award evidence. |
| `GET /api/reviewer/leaderboard-position?metric=distinct_stops&period=month&month=2026-09` | Owner-only private self-position, no arbitrary reviewer selector. Proposed rank among opted-in participants only, available when caller is opted in; otherwise return `rank:null, reason:'not_opted_in'`. Never return private neighboring rows. |
| `GET /api/community/activity` | Proposed conservative payload: bounded delayed summaries `{display_name,public_id,family,milestone_label,month}`, with current allowed display name and consent resolved on every read. No exact stops, coordinates, review timestamps or private evidence; no per-review feed. Scope labels are omitted from this proposal pending privacy review, not permanently ruled out. Scope detail and delay/coarsening remain unapproved. |

Initially expose only metrics whose semantics are approved: `distinct_stops`
and First Look claim count are separable candidates. Regional/route metrics
remain disabled until their definitions and prerequisites pass. A monthly
distinct-stop count deduplicates within the period; all-time deduplicates across
all qualifying history, including now-inactive stops. Monthly First Looks count
winning completions in the period, not the date a delayed processor ran.
Coverage leaderboards, if later approved, must identify dimension/snapshot and
must not blend incompatible denominators.

Propose descending value with competition ranks (`1,1,3`); stable public ID
orders ties for display only. Top-N truncates rows deterministically, with a
visible tie explanation. N and tie policy require approval. Private self-rank
uses the same metric, period and consent cohort, not a secret all-reviewer
denominator. Opt-in/withdrawal can change rankings immediately.
This proposed consent-dependent community self-rank is not a gate on private
progress, counts, achievements or next targets; self-rank presentation remains open.

**Time proposal:** use `America/New_York` for calendar months and activity month
labels; compute local midnight at the first day and next first day, convert each
boundary to UTC, then query `[start_utc, end_utc)`. Do not subtract 30 days or use
the server's timezone. For example March 2026 is
`[2026-03-01T05:00:00Z, 2026-04-01T04:00:00Z)`; its differing offsets are expected.
An explicit-offset input is normalized to UTC. SQLite-generated
`CURRENT_TIMESTAMP` values are UTC despite lacking offsets; interpret naive
legacy timestamps as UTC **only after confirming their generating path**.
Malformed, missing or provenance-ambiguous imported values are quarantined,
not guessed as Eastern time. Normalize to seconds and preserve original text
in the run manifest/evidence; unexpected subsecond precision needs a migration
policy before inclusion. Test timezone data availability in the hosted Python
environment. Return UTC boundaries and the timezone name in monthly responses.

## E. Profile and dashboard integration

The full `reviewer_profile.html` is the personal achievement home: all earned
achievements and dates, Explorer progress and next milestone, First Looks,
geography stewardship progress, additional useful next targets, eventual
certified route progress and future approved families. None requires public
recognition opt-in. Show route progress only after certification, with an
honest unavailable explanation beforehand. Keep existing stewardship and
ridership/exposure caveats separate; achievements imply neither stop ownership
nor measured rider impact.

Rank suggested targets by transparent proximity to a milestone and the
reviewer's selected geography/route context, not a combined points score.
Current active filtering applies to actionable targets. Do not list every
possible scope. Represent zero progress, ineligible scopes, unknown membership,
pending evaluation and exhausted milestones distinctly. Private target stop
links may use existing review routes; never leak them through community APIs.

For an authenticated reviewer, evolve the existing dashboard account/profile
area (`communityProfileCard`) into a compact **Your Progress** mini-card showing:

- Existing reviewer display name/account context.
- Distinct stops documented and/or First Look count.
- Next Explorer milestone.
- **One** especially relevant geography-stewardship target.
- **View your progress & badges** link to the full profile.

Illustrative private copy, not hard-coded reviewer data:

```text
Your Progress — Reviewer
42 stops documented · 42 First Looks
Explorer — 42 / 50
Community Steward — Arlington — 42 / 48 toward 10%
View your progress & badges →
```

```text
Your Progress — Reviewer
5 stops documented · 5 First Looks
Explorer — 5 / 20
Neighborhood Steward — ANC 6D — 5 / 10 toward 25%
View your progress & badges →
```

The mini-card is private and available regardless of public consent. Select its
single geography target transparently using the selected context and proximity
to a milestone; explain the selected scope, never an opaque points score. Do
not infer residence from contribution geography or list every geography/route.
For signed-out visitors, this area can explain documenting stops, tracking
progress, earning achievements and viewing coverage milestones with sign-in/join
navigation. Do not promise route badges before certification.

Recent community milestones and a small metric-specific top-N list remain
secondary to primary bus-stop network content. Preserve jurisdiction horizontal
scrolling, two frozen identifying columns, sticky headers and geography dimensions.

Render display names/labels with existing safe DOM/text practices, not interpolated
HTML. Loading/failure of community modules must not delay the map or break the
profile's existing content. Use responsive cards, keyboard-visible controls,
accessible progress descriptions and explicit counts as well as percentages.

## F. Consent, privacy and aggregate impact

Propose one clearly described public-recognition consent covering both named
leaderboards and delayed generic milestones; granular consent is an unresolved
product option. Default false for all existing/new reviewers. Require a
deliberate authenticated action with CSRF; never infer consent from past public
display names, review participation, profile visits, emails or steward status.
Before enabling, clearly explain: **Your reviewer display name may appear
publicly on community leaderboards and recent/community achievement activity.**
V1 uses the existing account display name, not a separate public alias. A future
alias enhancement is possible but is not a V1 schema/API/UI requirement.

The same consent explanation must say that recognition surfaces will not expose
email address, reviewer key, private numeric reviewer ID, exact reviewed stop
list, exact review coordinates/timestamps or private award evidence. Resolve
only the current allowed display name when current consent permits publication;
never derive a public name from email. A name change updates subsequent public
rendering but neither grants nor revokes consent. Private progress, earned
achievements, First Looks, geography targets, next milestones and eventual
route progress remain available without public opt-in: consent controls what
other people can see, not the reviewer's own experience.

Withdrawal filters the reviewer from public results immediately at query time;
retain private awards and consent history. Initially send public recognition
responses with `Cache-Control: no-store` to avoid stale server/browser rankings
after withdrawal. Do not copy display names into immutable achievement/activity
events. Already viewed or externally saved public content cannot be recalled;
explain that limitation in
consent copy without promising deletion from third parties.

Public activity detail is still unresolved. A conservative option is generic
cumulative milestones delayed at least seven days with earned month rather
than an exact date. Neither that delay/coarsening policy nor inclusion of
geography/route scope labels is approved yet. For example, "Display Name earned
Neighborhood Steward — ANC 6D" is under consideration, not an approved public
payload. Evaluate location-pattern disclosure and cross-endpoint linkage before
approving such detail. Exact stop locations and exact review timestamps remain
excluded regardless. Public IDs must not appear on observation/stop APIs, which
would enable linkage. Coarsening does not make named participation anonymous.
Complete the public activity privacy review before launch. Private award dates and
evidence remain owner-only. Logs/diagnostics must avoid emails, reviewer keys,
photo URLs and raw private evidence.

The completion ledger, First Look claims, snapshots and award witnesses can
support aggregate distinct stops documented, contributing reviewers, First
Looks, geography stewardship milestones, network/geography coverage progress
and eventually certified route coverage milestones. Do not infer volunteer
residence or personal impact from contribution geography. Count each entity at its
proper grain, not joined witness rows. Distinguish accounts, contributing
reviewers, unique stops and reviews, and identify active versus historical
populations. Propose suppression of small geography/time cohorts and coarse
time periods; the minimum cohort size and differencing controls remain privacy
decisions. Private participation must not be exposed via narrow aggregate
filters or by subtracting public counts. No supporter reporting endpoint,
exports, fundraising attribution or report generator is part of V1 planning.

## G. Idempotency, transactions and concurrency

1. In the later implementation, record the validated completion and unique job
   in the **same short transaction** that first successfully marks the assignment
   completed. Do not move the existing evidence commit or derived refresh.
   A retry for an already completed assignment can reconcile a missing job
   idempotently from persisted evidence. Never use the replacement payload.
   When recognition is disabled, retain the existing submission path; a bounded
   reconciliation command can ingest missed completions after re-enablement.
2. Completion recording has a PK on assignment and UQ on observation. On
   conflict, compare the immutable stored identity/time, not an unconditional
   overwrite. Quarantine a mismatch. No observation or photo updates occur.
   Failure before the completion transaction commits retains existing saved-
   evidence retry semantics. Worker/evaluation failures after commit do not
   turn a successful review into an operational error.
3. A worker leases a bounded batch in a short writer transaction, commits and
   closes before expensive work. Pin snapshot/rule versions, calculate against
   immutable evidence, then use a short `BEGIN IMMEDIATE` transaction to verify
   lease ownership and insert award, witnesses and event atomically. Unique
   keys provide idempotency across retries/workers, not a check-then-insert race.
   A crash rolls back the award group or leaves a renewable expired lease.
   On busy/error, release resources and leave work for a later bounded run;
   no timeout, WAL, prewarming or connection-lifetime workaround.
4. First Look needs more than `INSERT OR IGNORE` for the first processed job.
   Backfill the approved historical cohort before live adjudication. Process
   only closed completion-time seconds: the writer-locked adjudication queries
   all qualifying completions strictly older than the current SQLite UTC
   second, orders by time then assignment ID and chooses the earliest per stop.
   This prevents a lower-ID assignment completed later within the same second
   from losing solely because its job ran later. Reconcile all completed
   assignments through that cutoff before sealing claims; do not trust job
   delivery order. A claim transaction cannot overlap another SQLite writer.
5. First Look sealing assumes completion timestamps are immutable and generated
   monotonically enough for this cutoff, and imports/backfills are controlled.
   Audit existing non-submission writers before implementation. No late
   backdated imports into the live cohort without a paused reconciliation plan.
   An earlier timestamp discovered after a permanent award is a quarantined
   discrepancy, not automatic reassignment. Clock regressions, corrections and
   historic exceptions require an approved policy; do not claim absolute
   permanence plus unrestricted backdating are simultaneously solvable.
6. Rule versions are immutable. A new version does not award the same tier twice
   because award uniqueness excludes the version. New tiers need explicit
   product/migration approval. Store numerator, denominator, scope/version,
   completion witnesses, full membership snapshot, rule JSON/hash and evaluation
   time. Hashes alone cannot reconstruct evidence. Successful retries return
   existing accomplishments. Snapshot publications never erase awards.

No GET initiates any of these transactions. All connection-owning functions
close in `finally`/equivalent deterministic scopes and roll back on exceptions;
caller-owned connections remain caller-owned. Read results must be materialized
before close. Keep the SQLite lifecycle hotfix invariants and test real
file-backed multiprocess contention, not only mocks.

## H. Pilot historical backfill

Use an authorized backup/disposable copy first; this documentation task has not
accessed or changed production. Inventory exact schema, reviewer identity,
source values, completed joins, duplicate assignment observations, malformed
times, orphan evidence and completion-without-observation cases. Produce a
dry-run manifest with proposed awards and exclusions. Never fabricate missing
assignments, timestamps or evidence, and never rewrite pilot observations.

Propose backfilling global Explorer and First Look only where qualification is
provable. Explorer's historical earned date is the qualifying completion that
crossed the threshold under the approved rule. First Look selects winners from
the entire approved historical cohort before live processing. A run records
cutoff, algorithm/rule versions, input hashes/counts and exclusions. Re-running
must produce no duplicate completions, claims, awards or activity events.

Do not retrospectively award historical geography/route coverage using today's
membership. Show current progress from historical reviews intersected with the
current qualified snapshot. A separately approved one-time present-day award
could use that snapshot and today's earned date, explicitly labeled as such;
it is not assumed approved. Existing route joins omit inactive membership and
cannot establish historical route coverage. Historic awards do not flood the
public recent-activity feed. All migrated preferences remain off regardless of
display names. The supplied September 30 production calibration informs product
choices but is not a backfill manifest or approval. Revalidate production pilot
counts and qualification from the authorized implementation snapshot, not the
empty local history or an assumption that calibration created awards.

## I. Stable route identity prerequisite

1. Preserve feed provenance: source/agency namespace, content hash, service
   validity, native agency ID and native GTFS route ID, plus display names.
   A short name is presentation, never a globally unique identity. Missing
   feed-local agency_id requires a certified single-agency resolution, not an
   unqualified empty string shared across feeds.
2. Build the proposed side-by-side route registry/version tables and explicit
   crosswalk on a disposable database. Audit same short names across agencies,
   reused/changed native IDs, route splits/merges, feed replacement, overlapping
   service versions, unmapped GTFS stops and ambiguous physical mappings.
   Stable identity continuity requires documented operator decisions when feed
   identifiers change; never infer permanence solely from a route name.
3. Use trusted GTFS/member linkage to build active physical membership with
   DISTINCT IDs and mapping provenance. Deduplicate multiple members of the
   same physical stop. Record unmapped/ambiguous counts and quality gates per
   route. The >=10 candidate floor does not establish mapping completeness.
   Approve a minimum completeness policy before any coverage award.
4. Certify a route-version snapshot, compare operational counts and explicitly
   approve the crosswalk. Existing route selection, favorites and serving-
   direction code continue using their current contracts until separately
   migrated; this project is not authorization to rewrite them.
5. Only then activate route progress/awards with pinned certified versions.
   Freeze route identity, scope membership, N/D, witnesses and rule version in
   each award. No historical identity guesses to make pilot route badges appear.

## J. Geography quality prerequisite

Use independent State, County, Municipality, DC Ward and ANC scopes; do not
assume a universal hierarchy. Canonical DC wards reuse `canonical_dc_ward`.
Resolve names to namespace-qualified stable geography keys and record boundary
version/provenance; a display label alone is not permanent identity. A renamed
scope must not create duplicate lifetime awards accidentally.

The local feasibility snapshot had 46 positive-denominator ANCs, eight wards,
130 municipalities and six county categories. Twenty-nine municipalities had
fewer than ten active stops. It also exposed substantial missing municipality
coverage and questionable DC assignments: 2,115 active DC stops lacked a
municipality, 51 carried neighboring municipality labels and 55 had non-DC
county labels. These warrant investigation, not automatic corrections or a
claim that every dimension is ready. Null ANC/ward outside DC is not itself an
error; zero-denominator legacy scopes are ineligible.

Before publishing a scope, audit missingness in the applicable area, invalid
labels, canonical duplicates, multiple memberships, cross-border assignments,
boundary provenance and active denominator reconciliation. Distinguish valid
independent-city/county semantics from actual errors. Publish a coverage/quality
manifest with eligible scopes and explicit limitations. A verified dimension
may launch independently; label unsupported scopes unavailable, never zero
reviewer effort. Do not declare geography stewardship comprehensive until the
relevant data-quality gates pass. Quality tolerance and launch dimensions need
approval; this task does not repair geography data.

## K. Testing and acceptance plan

No tests are added or changed by this design task. Later implementation should
extend existing review/auth/lifecycle suites and add focused recognition suites.

- **Migration:** clean and current pilot schemas on disposable file-backed DBs;
  repeat migration; exact constraints/indexes/triggers; FK/integrity checks;
  preferences default off; no changed existing row counts; old application
  compatibility; explicit database path and no DDL on import/requests.
- **Qualification/backfill:** all matching/mismatching join combinations,
  duplicates/orphans, unknown answers, excluded sources, null/invalid/imported
  times, seconds/offsets, dry-run reproducibility, historical pilot fixtures,
  rerun idempotency and no mutation of review/photo evidence.
- **Rules:** threshold edges, ceiling rounding, D=0/9/10/99/100, minimum counts,
  independent dimensions, duplicate member joins, inactive/current intersections,
  identity splits and canonical ward variants. Current progress changes while
  frozen awards remain explainable and unchanged.
- **Concurrency:** real separate SQLite connections/processes, controlled
  barriers rather than sleeps; duplicate retries, refresh failure then recovery,
  simultaneous completions, same-second First Look ties in reversed job order,
  failed award/event insert, crashed/expired leases and interrupted backfill.
  Confirm locks release after exceptions and all subprocesses clean up. Test
  earlier unprocessed completions and clock/backdate quarantine explicitly.
- **Privacy/auth/API:** missing/forged sessions, reviewer selectors, CSRF,
  default-off display names, explicit opt-in/withdrawal, current display-name
  changes without consent changes, no required alias, private progress with
  consent off or preferences absent, public payload allowlists,
  no email/private ID/time/location leakage, no cross-API
  linkage, no-store responses, ownership of progress/self-rank, bounded paging,
  unsupported metrics and withheld small aggregates.
- **Calendar/ranks:** UTC-naive proven provenance, offsets, DST month boundaries,
  inclusive start/exclusive end, completion versus processing month, tie and
  top-N behavior, private self-rank consistency and consent cohort changes.
- **Routes/geography:** colliding agency short names, reused native IDs,
  incomplete/ambiguous mappings, tiny routes, duplicate physical members,
  renamed/versioned scopes and quality-gated unavailable states. No route award
  is possible before certification.
- **UI/browser:** approximately 320/375/390/430px, tablet and desktop; long
  geography/route/display-name labels; context-sensitive stewardship titles
  with one internal family and no duplicate awards; compact dashboard mini-card
  with one explainable target and full-profile navigation;
  keyboard/screen-reader descriptions; zero,
  loading, pending, unavailable and error states; safe rendering of malicious
  labels; useful bounded targets; no page overflow or sticky-table regression.
- **Integration/performance:** preserve `test_active_review_workflow.py`,
  `test_reviewer_auth.py`, `test_sqlite_lifecycle.py`, active-stop pipeline,
  serving-direction, Street View, HTML safety and sticky-column tests. Bound
  query counts and worker transaction durations; ensure public modules never
  block network map loading. Run focused suites, full suite, Python compilation
  and `git diff --check` for each implementation phase; record actual totals,
  not historical counts from audits.

## L. Implementation phases, deployment and rollback

1. **Approve semantics and audit prerequisites.** Confirm qualification source,
   timestamp provenance, still-provisional thresholds, First Look exceptions and
   privacy choices; preserve the selected V1 calculations above;
   inventory the authorized pilot snapshot and geography/route quality. Approve
   the proposed schema/API in an implementation review. No route prerequisite
   should block independently safe private Explorer work.
2. **Private foundation.** Implement offline additive schema, qualification,
   rule/evidence services, idempotent completion capture, bounded processor,
   dry-run backfill and tests, behind default-off flags. Establish historical
   cohort and First Look watermark before adjudicating live winners.
3. **Private progress.** Launch approved Explorer/First Look behavior and owner
   profile progress after verified backfill. Add geography families only for
   approved scopes/rules; route families remain off. Monitor backlog, retries,
   query latency and quarantine counts. Include the private dashboard Your
   Progress mini-card here, independent of public-recognition enablement.
4. **Public recognition.** Only after privacy review, add explicit consent,
   metric-specific top-N, optional owner self-rank and privacy-approved
   milestone modules. Empty public results are valid; do not auto-enroll pilot
   reviewers to populate the dashboard.
5. **Certified network families.** Complete route identity/mapping migration and
   outstanding geography gates, then separately approve/activate those families.
   Aggregate impact reporting remains a future consumer, not a deliverable.

Deployment follows [the existing runbook](reviewer-deployment-runbook.md): take
a verified backup and manifest with the web app/writers quiesced; set explicit
`DMV_BUS_STOPS_DB` for shell, worker and web process; verify database path,
integrity, FKs and pre-migration counts. Existing review schema setup remains
`python scripts/active/create_review_tables.py`; the future recognition
migration is a separate reviewed command, not invented as an executable step
here. Test it on a disposable copy first. Check new schema constraints and
unchanged source evidence/counts before startup. There is no migration at import.

Deploy additive support with all recognition flags off, perform the reviewed
historical dry run/backfill, start bounded processing, then enable private and
public phases separately. PythonAnywhere reload/restart and any recurring
processor scheduling are explicitly operator-specific steps. Smoke-test review
submission and exact retry, profile auth, default-off privacy, consent withdrawal,
active-stop/geography counts, map/detail latency, backlog recovery and SQLite
lock release. No production operation is authorized by this planning document.

Rollback first disables public recognition, then private evaluation/capture as
needed, and stops the processor. Existing review functionality must continue.
Retain additive tables and earned evidence; code rollback should not require
dropping them or reversing consent. Prove old-code compatibility on a migrated
copy, including any existing account-maintenance paths affected by new FKs.
Do not restore a pre-deployment database over newly submitted reviews as routine
rollback. Resume later through idempotent reconciliation. Database restoration
is a separate operator-approved recovery with an explicit plan to preserve
intervening contributions.

## Decisions still required

- Final badge/tier display names and edge-case geography stewardship vocabulary;
  Regional Explorer thresholds and minimum meaningful contribution per geography;
  cumulative First Look milestone thresholds/names; approval of the provisional
  Route Connector 3/5/10/20 milestone ladder.
- Geography size-band tier identity, initial eligible dimensions/quality
  tolerances, and whether network-only changes may trigger an award.
- Certified route identity/continuity/crosswalk process, completeness policy,
  candidate >=10-stop eligibility floor and historical versus current route
  contribution semantics.
- Historical cohort exceptions, naive imported timestamp provenance, First
  Look late discoveries/backdating/clock regressions, and any present-day
  catch-up award policy for network families.
- Anonymous-session private progress versus verified-sign-in-only launch.
- Public activity geography/route scope detail and delay/coarsening policy;
  consent granularity if more than one public-recognition switch is needed;
  aggregate privacy suppression/differencing rules.
- Public top-N limit, tie presentation, approved initial metrics and self-rank
  policy. No opaque score is an option.
- Operator scheduling/latency expectation and storage/retention sizing for
  immutable membership/evidence. These are implementation/deployment decisions,
  not permission to weaken permanent evidence or public privacy.

Already selected, not reopened by this list: Explorer 5/20/50/100; the geography
size-band calculation; Route Coverage 25/50/75/100 once certified; the >=3-stop
Route Connector qualifying-route definition; existing display name after
explicit public consent; private progress regardless of public opt-in; and the
dashboard account area's miniature Your Progress surface. Selection does not
waive route/geography certification or authorize production awards.

None of these unresolved choices authorizes changing current application
behavior. This design is ready for product/implementation review, not a claim
that achievements or public recognition are ready to deploy.

# Controlled private First Look and Geography Steward

This is an additive disposable-rehearsal release. No production migration,
capture, issuance, worker, scheduler or HTTP writer is enabled. Explorer's seven
tables, rules, jobs, services, witnesses and production binding are unchanged.
Explorer-only databases/API responses remain supported. The existing adjudication
reports remain read-only and do not authorize issuance.

## Approved launch rules

First Look is one permanent private claim per physical stop, without a cumulative
tier ladder. A reviewed full-population reconciliation supplies an exclusive UTC
cutoff, expected assignments, clock review and identity review. Every qualifying
competitor must have matching immutable completion evidence. The existing
qualifier/report orders by completion instant then numeric assignment ID.
Unsupported timestamps, corrected evidence, identity edges/non-current identities
and invalid competitors withhold affected stops. Missing history, orphan
competitors and unattributed identity events block the operation. Historical
inactive stops remain eligible; successor credit never transfers.

Sealed evidence preserves withheld cases and winners. Late discoveries do not
reassign/delete claims. `append_discrepancy()` appends separately reviewed
evidence/reference/date with a deterministic key and explicit authorization.
Automatic correction/revocation is outside this release. Review references are
operator attestations; unrecorded clock errors cannot be inferred from SQLite.

Geography is one present-day catch-up per certified scope. Completion cutoff
equals the explicit evaluation/earned instant. Historical reviews intersect the
approved snapshot: present-day coverage at evaluation, not historical geography.
Stable ordinal tiers retain lifetime identities independently of size bands:

| Snapshot D | Percentages for tiers 1–4 | Required count |
| --- | --- | --- |
| Below 10 | None | Ineligible |
| 10–99 | 25, 50, 75, 100 | max(5, ceil(D × percentage / 100)) |
| At least 100 | 10, 25, 50, 75 | max(10, ceil(D × percentage / 100)) |

These are the existing design/report defaults; custom permanent thresholds are
rejected. All N distinct-stop witnesses are retained, overlapping between tiers.
Percentage, band, N/D, snapshot and rule are frozen. A later denominator shrink
cannot initiate another catch-up. Continuing issuance/new snapshots require a
separately reviewed extension preserving reviewer/scope/ordinal-tier uniqueness.

## Additive schema and transactions

`permanent_schema.migrate(database)` rehearses in memory by default. Explicit
`apply=True` installs only these new tables transactionally; compatible existing
Explorer schema is required. Nothing imports migration into application startup.

| Table | Purpose / uniqueness |
| --- | --- |
| `recognition_private_rules` | Immutable new-family rule definition/hash |
| `recognition_private_operations` | Full reviewed manifest/report, authorization reference, actual sealing time; canonical manifest digest is operation ID |
| `recognition_first_look_claims` | One claim per physical stop; unique winning completion |
| `recognition_first_look_discrepancies` | Append-only content-addressed review evidence |
| `recognition_geography_scope_identities` | Stable key, unique dimension/canonical identity, frozen display label |
| `recognition_geography_snapshots` | Certified scope JSON/hash; one launch snapshot per scope |
| `recognition_geography_members` | Exact distinct active members per snapshot |
| `recognition_geography_awards` | Lifetime reviewer/scope/ordinal-tier uniqueness; frozen evidence/catch-up date |
| `recognition_geography_witnesses` | Award/completion pairs referencing existing immutable ledger |

All rows reject UPDATE, DELETE and INSERT OR REPLACE, even with recursive
triggers disabled. Foreign keys never cascade deletion. Historical references
restrict account/stop deletion; future retention/correction policy requires
explicit design. Retain manifests and external evidence privately.

`prepare()` is read-only. `finalize()` defaults off and requires the reviewed
canonical manifest hash, matching explicit authorization reference and
`RecognitionGate(capture=False, issuance=True)`. It owns `BEGIN IMMEDIATE` and
validates schema/trigger definitions, then regenerates the complete report,
identity history, ledger and candidate set before its first insert. Reports use
a SELECT-only authorizer inside that connection. No Explorer job is leased or
finalized, and missing completions are never captured by this path.

The entire operation, snapshot publication, claims, tiers and witnesses commits
atomically after integrity/FK checks. Exceptions roll back all operation records.
Identical retries verify durable records without re-earning from current data.
Different operations cannot overwrite claims or reopen a scope catch-up.
Integrity checks cover rule/evidence hashes, owner/context, frozen candidate
mathematics/ordering, ledger witnesses and snapshot membership. SHA-256 is change
detection, not a signature or independent certification.

## Reviewed inputs

```python
from src.review.recognition.permanent import prepare
from src.review.recognition.rules import canonical, digest

manifest = prepare(
    offline_database,
    family="first_look",  # or "geography_steward"
    inputs=reviewed_report_inputs,
    evaluation_at_utc=reviewed_evaluation_instant,
    authorization_reference=independent_operation_review_reference,
)
# Privately retain canonical(manifest), independently review candidates AND
# exclusions, and record digest(manifest) plus SHA-256 of exact saved file bytes.
```

First Look inputs are `build_report()` keyword arguments. Never invent a cutoff,
provenance or reconciliation. Geography inputs are `build_geography_report()`
arguments without `thresholds`. Every scope additionally requires a nonblank
`display_label`, `identity_review_reference`, `quality_findings: []` (no unresolved
findings), and `certification.independent: true`. Existing approved certification
reference, source/boundary hashes, stable identity/version, capture/effective
timestamps and membership hash remain mandatory. Exact members must each have
integer `current_gtfs: 1`, also equal to 1 in the locked evaluation copy.
No current labels, border overlay or pending evidence package substitute for
certification. Complete membership and referenced external evidence require human
review; the service cannot prove them by inspecting reference strings.

## Exact disposable rehearsal procedure

Run from this checkout, replacing placeholders with reviewed offline artifacts.
`--manifest-sha256` means exact-file SHA-256; the service separately verifies the
canonical digest. PowerShell verification-only command (creates no output):

```powershell
python -B scripts/active/rehearse_private_recognition.py --source '<absolute-offline-copy.db>' --source-sha256 '<SHA256>' --manifest '<absolute-reviewed-manifest.json>' --manifest-sha256 '<FILE_SHA256>' --target "$PWD/.tmp/private-recognition-rehearsals/disposable-first-look.db"
```

After review and explicit disposable issuance authorization:

```powershell
python -B scripts/active/rehearse_private_recognition.py --source '<absolute-offline-copy.db>' --source-sha256 '<SHA256>' --manifest '<absolute-reviewed-manifest.json>' --manifest-sha256 '<FILE_SHA256>' --target "$PWD/.tmp/private-recognition-rehearsals/disposable-first-look.db" --apply-disposable --authorization-reference '<EXACT_REVIEW_REFERENCE>'
```

Geography uses its own reviewed manifest and `disposable-geography.db`. Repeat the
identical authorized command with `--retry-existing` to verify idempotency; it
requires the original receipt and target filesystem identity. Never rename an
application database into the reserved directory. There is **no production mode**,
binding override, capture option or network use. The command exclusively creates
a new byte-identical disposable copy, applies additive migration there, seals the
reviewed candidates and confirms Explorer rows/source bytes remain unchanged.

Only offline rollback-journal snapshots are accepted. Keep writers stopped and
the private directory free of competing filesystem writers. Orderly failure
rolls back sealing; the receipt supports retry. On a hard termination/hot journal
the command stops: never delete journals or restore over a database. Retain the
failed disposable copy for inspection and authorize a fresh uniquely named copy
from unchanged source. Production recovery/provisioning is a separate review.

## Private display and production blockers

Explorer display fields are unchanged. First Look exposes family, claim kind and
earned timestamp, never stop IDs or witnesses. Geography exposes label, ordinal
tier, frozen N/D/percentage and catch-up date. Every owner record is integrity
checked in the same read-only snapshot. Existing authentication, private/no-store
responses, safe DOM text rendering and logout/visibility clearing remain in use.
Current progress/report candidates never become awards through these reads.

Synthetic tests cover Explorer compatibility, migration repeat/rollback, complete
competitors, races, identity exclusions, atomic sealing, discrepancies, fixed
tiers/snapshots, default-off/target/hash checks, privacy and rendering.

No production manifest or binding is created. Production preparation remains
blocked on a reviewed First Look population/cutoff/clock/identity reconciliation,
explicitly certified initial geography scopes and retained evidence. Missing
ledger evidence needs separately authorized existing capture. Explorer's binding
does not authorize these families. A separately reviewed new-family production
target/operation procedure and verification must precede production migration or
issuance; this release supplies the disposable rehearsal, not that authorization.

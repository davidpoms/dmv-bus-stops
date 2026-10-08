# Private cross-dimension evidence adjudication

`src.review.recognition.cross_dimension.build_cross_dimension_report(packages)`
is a pure function accepting a mapping with exactly `dc_ward`, `dc_anc`,
`county`, `state`, and `census_place` package envelopes. It opens no paths,
databases, or URLs, and performs no recognition operations. Do not supply a
database. The five original evidence packages remain unchanged.

The output format is `geography-cross-dimension-adjudication-v1`, with
`purpose: evidence_adjudication_only`, `certification_action: none`, and
`issuance_ready: false`, including quarantined results. It is not a certified
scope snapshot or an input authorizing issuance.

## Independent comparisons

Explicit adapters handle Ward's subset identity-state and separate coordinate
membership lists, ANC polygon matches, County coordinate GEOIDs, State pipeline
results, and Census Place discoveries and embedded State evidence. Supplied
memberships remain arrays. Discovery never replaces supplied membership.

The builder derives conflicts from these assertions, source catalogs, and stored
labels. Package `quality_checks` indexes are not reconciliation authority and
are not used to generate findings. State memberships are compared with County
and Place state assertions. County and Place identities remain separate Census
geographic levels; independent-city comparisons retain their classifications.
ANC identities such as `3/4G` are never parsed as ward hierarchies.

Each stop/dimension includes supplied memberships, discoveries, labels, absence
status, the assertions compared, assessment, unresolved evidence, classification
notices, and identity status. Findings distinguish contradictions, classification
notices, absence, identity involvement, and unresolved evidence. Missing evidence
never means agreement. Crosswalk candidate sets compare case-folded labels with
whitespace collapsed; no source labels or identities are rewritten.

## Validation and limitations

Canonical payload, scope metadata, membership, and Ward supplementary-list
hashes are verified from the supplied JSON. Repeated named source-artifact hash
claims must agree. Embedded snapshot manifests must identify the declared copy.
Census Place's State reference and embedded stop evidence must agree with the
supplied State package. Source-artifact bytes and original manifest file bytes
are unavailable: their hashes are assertions, not independently verified files.
Checksums are consistency checks, not authenticity or certification.

The adapters validate matching active denominators, snapshot identities, and
identity event/edge histories before reconciliation. Fundamental inconsistencies
return `status: quarantined`, stable error codes and validation details, and no
normal stop records. No partial report escapes on failure.

Full-history packages require identity-state coverage of the active universe;
Ward requires coverage only for its represented subset. Missing rows or missing
edge endpoint state evidence produce explicit uncertainty and blockers, not
`manual_exception: false`. Unknown manual-exception status is null. References
to nonexistent identity events are rejected. Retired predecessors need not be
active. Events without edges are global blockers. State rows establish supplied
identity evidence, not independent proof that an inactive physical-stop row
exists; this pure report cannot verify a database inventory it was not supplied.

CRS compatibility, effective dates, historical attribution, identity history,
crosswalks, provenance, and independent certification remain unresolved. This
report neither transforms coordinates nor allocates predecessor credit.

## Determinism

Stops, findings, candidate sets, and intersections use deterministic ordering.
Intersections include counts and sorted stop IDs; exact finding-combination
groups expose higher-order overlap. No generation timestamp or local file path
is added. `report_sha256` hashes the canonical report excluding itself.

Identical inputs and reordered mapping keys yield identical hashes. Changing
scope or membership list order and resealing changes the supplied canonical
package hashes (JSON lists are ordered). Interpretation and intersection counts
remain the same, but provenance-bound report hashes correctly change. The report
must not discard that distinction to claim identical input identities.

Tests use synthetic package schemas and no real private evidence or databases.
Scaled fixtures test inspected overlap sizes as set arithmetic; they do not
claim to reproduce or validate the historical cohort.

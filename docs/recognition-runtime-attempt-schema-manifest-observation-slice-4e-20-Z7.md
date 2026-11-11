# 4e-20-Z7: original attempt-phase schema/manifest observation

This implements only the control object-inventory subset of Z6 observation M.
The inventory is the exact `(name, sql)` sequence used by the existing normalized
manifest digest algorithm. Expected definitions, package recognition, migration
audit/predecessor/binding relationships and manifest projections are still
validated by their original readers. No row validator or whole manifest-transition
validation result is retained. History, profile, claim and complete-control
continuity are not implemented.

The coordinator creates an opaque, nonserializable token immediately after its
successful complete pre-insert `_evaluate()` in `_persist_attempt()`. Its immutable
private facts record the original process/thread, connections, phase identity,
reservation epochs, complete scope and authority, credential-scope digest,
physical observations, source mutation counters, observation time and normalized
schema digest. The token exposes no SQL, handles, callbacks or transaction methods.
No public constructor or reader parameter accepts a supplied proof.

Only the original attempt `_finish()` can activate routing to these facts. Before
reuse it checks the original registered owner, current deadlines and physical
identities, the exact attempt/genesis rows, protected authentication baseline,
exact single audit suffix and exact three control changes. It rereads the schema
inventory and database isolation at that boundary. The existing authorizers
continue to deny DDL, attachment, transaction/mode changes and other writes.
Every inventory use rechecks original ownership, connections/epochs, scope,
definition-code identity, physical identities and mutation counters. The original
validators still regenerate and compare expected definitions, including their
current constants. Authorizer-observed extra DML invalidates the observation even
if a statement affects zero rows; its existing authorization decision is unchanged.
A foreign connection uses its own
fresh inventory. No observation crosses issuance-to-attempt, commit, rollback,
cleanup, reservation reacquisition or metadata-owner entry.

The ContextVar holds routing for this one synchronous finalization; it is not a
process cache. Facts live on the original state and are destroyed on failure,
finalization and cleanup. Consumer failure poisons the owner. Existing denial
finalization receives no continuity and retains its original fresh path.

The final validator still freshly checks authentication and expiry, operation,
proposal/ACK/approval, dependencies, activation, emergency stop, readiness,
physical identity and target schema, current control rows, full history/audit
head, claim graph, new attempt graph and global foreign keys. All migration
relationship checks remain fresh too. Control commits while the target query-only
reservation remains held. No target DML, metadata entry, writer or execution is
introduced. Authority lifetime remains 120 seconds with all earlier bounds.

The focused test compares genuine coordinator finalization using fresh inventory
reads and observation-backed reads on the same restored disposable installation.
It uses a live UTC/monotonic clock, never a deadline extension. The diagnostic
artifact is `.tmp/recognition-z7-final-timing.json`; timing and SQL counters cover
the measured final-validation path. This is not a complete Z/metadata validation
or a guarantee that a G+2 metadata lifecycle fits its authority deadline.

## Focused result and limitation

The final focused run passed **2 tests and 29 subtests in 162.88 seconds**. It used
the existing genuine disposable coordinator fixture, not the complete G+2 Z
metadata path. Both finalizations completed under a live clock. Observations
were consumed only inside the original attempt finalization and discarded before
publication. Isolated negative predicate probes use the genuine registered owner;
authorizer-only tests use an unregistered state and cannot mint an observation or
grant authority. No authentication or admission validator is replaced by a stub.

| Final validation | Fresh inventory | Observation inventory |
| --- | ---: | ---: |
| Elapsed seconds | 18.147 | 30.732 |
| Schema SELECTs | 18,274 | 2,124 |
| Total SELECTs | 54,568 | 38,418 |
| PRAGMAs | 20,290 | 23,885 |
| Global FK PRAGMAs | 1,041 | 1,041 |
| Audit SELECTs | 18,658 | 18,658 |

Profile, claim, activation and approval SELECT counts and all eleven watched live
validator call counts were identical. Both paths produced the same schema digest,
scope and subject and committed the exact inert attempt graph. The comparison
does not require random attempt/authority UUIDs to be identical. Neither final
path performed target DML or invoked a writer/execution path.

**Inventory reads decreased, but elapsed time regressed.** Per-use ownership and
physical-identity checks add work (query-only checks increased from 17,991 to
21,586). This is not a final-validation speedup or evidence that Z fits its
120-second ceiling. Z remains BLOCKED; no Z, T or broader suite was run. No
additional optimization or lifetime change is authorized by this result.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED

# Slice 4e-20-Y: trusted-local runtime enrollment and atomic finalization

`enroll_transition_runtime_profile` in `runtime_enrollment_transition` implements
only U's existing SCHEMA_BOUND/B1 -> P1/B2/FINALIZED ceremony. It reuses V's tables,
codecs, insertion guards and deferred relationships. No schema is added.

## Trust and inputs

The API takes the existing 2c review, in-memory nonce, explicit operator/reason,
approved review/observation hashes, confirmation flags and expected scope, plus
the exact plan ID/digest. These are expectations, not credentials. Trusted host
access and independently reviewed private WSGI logs establish provenance;
unsigned hashes, nonce possession and confirmation flags do not authenticate a
worker. Browser claims cannot enroll a runtime.

The CLI adds `enroll-transition-runtime-profile`. It requires all existing
enrollment scope/digest/confirmation arguments plus `--plan-id --plan-sha256`.
It reuses the bounded protected-file checks and hidden getpass prompt. There is
no nonce argument/environment/file input or web route. Errors are sanitized.
The initial `enroll-runtime-profile` ceremony retains its pending-plan denial.

## Fresh validation and transaction

Control BEGIN IMMEDIATE precedes target BEGIN IMMEDIATE/query_only. The owner
resolves the unique unfinished plan, complete PREPARED/INTENT/SCHEMA_BOUND graph,
current B1/G+1/null profile and original P0. The existing V readers validate exact
binding continuity. Strict deployment identity, actual full H1, exact X package,
owner/auth/MFA epochs, pinned nonactive activation head and deadline are checked.
Unsettled runtime/legacy work, orphan ACKs/proposals or target markers reject.

The ordinary 2c review/nonce validation is shared without changing its semantics.
The durable challenge must be unused, current, exact-scope and unexpired. Review
observations must agree; every physical runtime field must exactly match P0,
including hostname, both paths and both devices/inodes. Only schema changes to
H1. Runtime rotation/device drift is not permitted by this ceremony.

Within one control transaction, revoke proofs/sessions, remove step-ups, consume
confirmations and nondestructively invalidate approvals. Compute the existing
profile at G+2 with unchanged 2c fields and its exact audit position. Insert the
FINALIZED event first, then P1/B2 and the unchanged enrollment audit, followed by
the linked finalization audit. V's deferred FKs and guards require the complete
graph at commit; there is no committed P1/G+2-prepared state or finalize-later API.

Before manager commit, revalidate complete control/runtime history, deployment
identity/H1, unchanged query-only target rows, emergency-stop head and fresh time
against both challenge and plan deadlines. Commit control while target remains
reserved; independently verify committed control history before returning DATA.
Target is always rolled back/released: zero target DML and zero target commits.
No administrative encryption-key contents are read.

## Repeats, uncertainty and inspection

Matching retry, conflicting profile, stale generation/digest, expired plan or
challenge and already-finalized plan all reject; no renewal/adoption/replacement
exists. SQLite serializes competing callers; a loser rejects current history or
propagates BUSY/LOCKED without retry loops.

Any uncertain commit/cleanup returns no usable result. Read-only
`inspect_runtime_profile_transition` delegates to V's structural historical
inspection: SCHEMA_BOUND means G+1 remains pending; FINALIZED means the atomic
control graph exists. Partial/corrupt P1/G+2 graphs are CONFLICTING_OR_UNCERTAIN,
not resumable preparation. Inspection does not jointly verify the target or
authenticate a runtime, and never authorizes retry. Missing data proves neither
success nor rollback. A new process must inspect, never adopt a live continuation.

## Scope and validation

Production remains NOT_ACTIVATED. New authentication and independently reviewed
activation authority are still required. Old approvals/authorities/attempts are
not rebound or promoted; historical records remain inspectable. There is no
writer admission/capability, target entry, family mutation, execution, completion,
seal, recovery, legacy claim/EXECUTING or activation producer.

Focused tests use disposable real W migration, 2a challenge and 2b collector
fixtures, hostile scope/review input, failed insertion, commit uncertainty,
concurrent finalization and explicit authority denials. Only the Y test file and
`git diff --check` are requested, with the specified isolated-failure stop policy.

Next: **retry 4e-20-T target-entry storage/migration using the finalized G+2
runtime profile plus the independently required activation authority.**

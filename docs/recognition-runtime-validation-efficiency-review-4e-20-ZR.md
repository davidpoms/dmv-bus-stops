# 4e-20-ZR: bounded history/manifest validation efficiency

ZR changes only schema projection inside one invocation of
`runtime_enrollment_transition_schema.historical_manifest()`. It does not approve
Z or T, create authority, alter lifetime, remove PRAGMAs or change ownership.

## Call/ownership inventory

Coordinator `_phase()` takes control BEGIN IMMEDIATE, validates history, takes
target BEGIN IMMEDIATE/query-only, then runs `_evaluate()`. Issuance and attempt
creation are distinct phases with fresh connections/reservations. `_persist_attempt()`
calls `_evaluate()` again before its fixed control writes; `_finish()` repeats
`_evaluate()`, `_final_attempt()` checks the inserted graph and `_history()`, and
the manager commits control before target reservation cleanup. Nothing in ZR
changes this ordering or reuses a result across any of these boundaries.

`_evaluate()` calls shared admission and issuer `_subject_for_owner()`. Session,
approval, proposal and readiness readers repeatedly call shared `_view_parts()`;
its coordinator branch calls `_read_parts()` -> `_current()` -> issuer `_current()`
-> runtime `_identity_snapshot()` -> `_history()` -> `check_control()`.
`check_control()` validates profile, claim, authority, attempt and transition rows.
Historical manifests nest: claims `check_rows()` -> authority
`historical_claim_manifest()` / `check_manifest_transition()` -> attempt
`authority_manifest()` / `check_manifest_transition()` -> V `historical_manifest()`.
Repeated calls are real nested invocations, not a retry loop. They borrow the
same reserved connections within a phase; the readers do not open connections.

All direct callers of V `historical_manifest()` are V `check_rows()`, attempt
`check_manifest_transition()` (installed and predecessor projections), and attempt
`authority_manifest()`. The latter two are themselves called repeatedly through
the claim/authority manifest chain. V's own `historical_manifest()` formerly
called claims `manifest()` three times after reading the same sqlite_master rows.

All callers of runtime `_history()` are:

- runtime validation `_identity_snapshot()` and `authentication_transaction()` entry;
- activated owner `_evaluate()` and transaction entry;
- authority issuance `_subject_for_owner()` and transaction entry;
- authority consent `_subject()`;
- coordinator `_phase()` and `_final_attempt()`;
- approval, claim and authority-consent transaction entry;
- proposal transaction entry;
- claim disposition `inspect_claims()`;
- authority/attempt/claim/V schema migration entry;
- W transition prerequisite/final validation and post-commit verification;
- metadata owner evaluation and entry (not entered in the ZR diagnostic).

Other modules' identically named event/operation `_history()` functions are
different readers, not calls to runtime binding history.

## Smallest permitted reuse

The original V reader already held `actual`, an exact sqlite_master mapping, to
verify every recognized extension definition. ZR normalizes that mapping into a
local tuple and derives the installed, predecessor and requested excluded
digests from it. The digest algorithm and exclusions are unchanged. Audit,
predecessor, installation and migration-scope checks still execute every time.
There is one definition read instead of four per invocation with V present.
Without V, the original claims manifest reader is unchanged.
Reuse additionally requires the exact native SQLite connection type and an
active transaction. Unreserved calls and unknown adapters retain all four original
reads, preserving adapter-specific ownership checks. Tests exercise both fallbacks.

This is a local immutable schema observation, not an auth/activation verdict or
an exported observation API. It is neither supplied by a caller nor retained on
an owner, connection, thread, process registry or global cache. The function does
no writes, yields, mode changes, reservation changes or external callbacks.
The projections use only that invocation's already-read definitions. Each next
invocation starts over, even with identical arguments on the same connection.
Consequently transaction, reservation epoch, process/thread, authentication,
activation, generation, mode and mutation boundaries cannot reuse the tuple.
All owner checks and final fresh validations remain in their existing callers.

The larger repeated `_history()` / `_identity_snapshot()` work is deliberately
unchanged. Carrying their results across authenticated reader calls would require
proving denial mutations, lifetime, freshness, physical observations and every
owner boundary safe; ZR does not assume that proof.

## PRAGMA inventory

The new bounded diagnostic counts only recognized PRAGMA names, never arguments,
SQL text or row contents. Across traced disposable connections it measured:

| PRAGMA | Count | Purpose; decision |
| --- | ---: | --- |
| query_only | 251,996 | Guarded handle/cursor/owner checks and fixed mode setup; retained |
| foreign_key_check | 13,609 | Profile/claim/authority/attempt/transition graph checks; retained |
| database_list | 9,058 | Isolation and physical database identity; retained |
| application_id | 2,244 | Target schema fingerprint observation; retained |
| user_version | 2,244 | Target schema fingerprint observation; retained |
| table_info | 3,007 | Schema/row inspection; retained |
| integrity_check | 16 | Disposable installation/transition integrity; retained |
| foreign_keys | 5 | Connection initialization; retained |

No traced journal/WAL or synchronous PRAGMA appeared in this run; existing
connection configuration and journal semantics were not changed. The aggregate
is not a census of statements issued on connections outside the diagnostic's
traced `administration.connect()` path. `query_only` is specifically not treated
as invariant: mode/reservation changes and manager-owned handle checks matter.

## Measurements and validation limits

The test-only pre-ZR reader is retained as an equivalence/timing oracle. Over 20
calls on the same disposable cloned control store, definitions reads fell from
80 to 20, and elapsed time from 0.047506 to 0.031171 seconds. Digests matched.
These are observations, not timing thresholds in tests.

Before: the 180-second diagnostic stopped during issuance final validation with
38,109 V manifest calls / 112.226 seconds exclusive, 1,689 history calls and zero
metadata-owner evaluations. After: one bounded run reached confirmed attempt
creation at 215.451 seconds elapsed, deliberately interrupted before metadata
entry (pytest: 216.54 seconds, three subtests passed). It measured 55,798 manifest
calls / 107.801 seconds exclusive, 2,219 history calls and zero metadata evaluations.
The total windows cover different progress and must not be compared as an
end-to-end speedup ratio. Manifest cost per invocation decreased; the actual
creation phase took 73.699 seconds. Authority lifetime remained 120 seconds;
its age at confirmed creation was 93 seconds, with 27 seconds remaining.

The test-only diagnostic has a 240-second cooperative bound plus a 15-second
hard watchdog, and a ZR-only stop after genuine `_create_attempt()` returns.
The intentional interruption does not publish a usable continuation and is not
a passing full Z test. No metadata-owner code was entered. The remaining Z
success/failure cases are unvalidated; no T work is authorized by these results.

Focused tests cover exact digest/read-count equivalence, fresh calls after
connection/transaction/mode/data changes, independent process/thread reads,
changed schema/audit/installation rejection, auth/MFA changes and corrupted
activation/generation data. Restoring exact dropped guards in corrupted memory
clones prevents schema drift from masking historical integrity rejection.
Manifest inspection never substitutes for authoritative activation/auth checks.
No deadline code or security owner implementation changed.

Final focused file: **11 passed in 6.23 seconds**. The coordinator diagnostic
preceded the final native-connection/active-transaction fallback guard; its
reserved native connection path is unchanged by that guard. It was intentionally
interrupted after confirmed creation, not reported as a passing Z test.
`git diff --check` passed. No broad validation was run.

No broad suite, hosted/production resource, deployment key, commit or push.
Next boundary: resume bounded Z metadata-owner validation separately, without
extending any deadline. T remains gated on Z approval.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED

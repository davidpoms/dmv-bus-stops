# SQLite connection-lifecycle hotfix

Baseline: `8513f53`. No deployment, production configuration change, migration,
commit, or production data mutation is part of this patch.

## Defect and scope

Legacy helpers closed connections only after successful execute/commit/fetch.
A busy commit could leave its write transaction and rollback journal alive while
an exception traceback retained the connection. A separate reader process and
file-backed SQLite test reproduced this: even after releasing the intentional
reader, an independent connection still failed with `database is locked` before
the fix. This demonstrates a real failure mode; it does not conclusively identify
the original production lock holder.

The fix uses explicit exception rollback for vulnerable writers and `finally`
closure for function-owned connections. Successful commit locations, query_db's
execute/commit/fetch order, parameters, row factories, return values, SQL predicates,
and evidence transaction boundaries are preserved. Some SQL string indentation
changes with the enclosing try block; SQL content is otherwise unchanged.
No timeout, retry, journal mode, WAL, new DDL, or database-layer abstraction is added.
Closure also happens if rollback itself raises. Existing close-on-failure paths
roll back pending work through SQLite connection close.

## Request-path connection inventory

| Module / function | Ownership and access | Disposition |
|---|---|---|
| `api/app.py:get_wmata_history` | Function-owned read | Add finally close |
| `api/app.py:get_wmata_evidence` | Function-owned read | Add finally close |
| `api/app.py:query_db` | Function-owned read/write | Roll back exceptions, finally close; preserve commit-before-fetch |
| `api/app.py:get_serving_directions` | Function-owned read | Existing finally close retained |
| `api/app.py:review_attachments` | Function-owned read | Existing finally close retained |
| `api/app.py:get_stop_evidence_summary` | Function-owned read | Add finally close |
| `api/app.py:create_observation` | Function-owned write | Add exception rollback and finally close |
| `api/app.py:validation_update` | Function-owned write | Add exception rollback and finally close |
| `api/app.py:seating_opportunities` | Function-owned read | Existing read-only URI and closing context retained |
| `api/app.py:submit_review` evidence connection | Function-owned write | Existing transaction context/finally retained; move FK setup inside try |
| `api/app.py:submit_review` refresh connection | Function-owned read/write | Existing finally retained; move row factory setup inside try |
| `api/app.py:review_queue` | Function-owned read | Add finally close |
| `api/app.py:rider_exposure_map` | Function-owned read | Existing read-only URI and closing context retained |
| `api/app.py:save_reviewer_routes` | Function-owned write | Add exception rollback and finally close |
| `api/app.py:_auth_db` | Factory transfers ownership to caller | Close if setup fails; successful return still transfers ownership |
| `api/app.py:reviewer_profile_api` POST | Function-owned write | Existing finally close retained; failed transaction rolled back by close |
| `api/app.py:pipeline_geography` | Function-owned read | Existing finally retained; move row factory setup inside try |
| `review/assignment_router.py:get_or_create_reviewer` | Function-owned read/write | Add exception rollback and finally close, including existing-reviewer return |
| `review/assignment_router.py:stop_is_active` | Function-owned read | Add finally close |
| `review/assignment_router.py:assign_stop` | Function-owned read/write | Add exception rollback and finally close, including all early returns |
| `review/consensus.py:calculate_stop_consensus` | Function-owned read/write | Add exception rollback and finally close, including no-observation branch |

`_auth_db` callers: role/owner decorators, admin page/summary, reviewer-management
page, role updates, verification, and profile-page checks already use finally
closure. Their behavior is retained. `reviewer_sign_in` previously closed only
on success and enumerated error types; it now closes in one finally block,
including unexpected exceptions. Existing auth helpers retain their explicit
commit/rollback behavior and never own the caller's connection.

Caller-owned consumers intentionally unchanged: attachment insertion/history;
review auth/admin helpers; serving-direction/member-linkage queries; exposure-map
queries; canonical amenity synthesis, review-priority refresh, queue refresh and
`build_opportunities`. Their owning request functions close the connection.
Existing downstream transaction contexts and schema operations are not moved or
expanded by this hotfix.

## Offline connections deliberately unchanged

No normal Flask request imports or calls these connection-owning entry points:

- `scripts/active/create_review_tables.py`: explicit offline schema migration.
- `review/create_review_queue.py`, `create_stop_review_assignments.py`,
  `create_stop_observations.py`, `export_review_tasks.py`, `submit_stop_review.py`,
  `complete_stop_review.py`, `update_recommendations_from_reviews.py`: CLI/offline
  queue, export, submission and processing utilities.
- `assessment/generate_seating_improvement_opportunities.py:main`: offline
  connection wrapper; the request path calls only caller-owned `build_opportunities`.
- Other assessment/scoring generators, ingestion, physical-stop processing,
  reporting, project utilities, database initialization/repositories, and static
  dashboard generation/data helpers: not reached by this Flask request graph.

Their broader cleanup is deferred. No migration is imported or executed at app
initialization; there is no global application SQLite connection or connection
teardown hook. Connection owners handle cleanup directly.

## Tests and validation

`tests/test_sqlite_lifecycle.py` adds 14 tests covering execute, commit and fetch
failures; success order/parameters; reviewer, assignment and consensus failures;
direct API writer failures; read failures; early returns; rollback failure;
auth setup/unexpected sign-in failures; and file-backed cross-process contention.
The subprocess handshake and exit waits are bounded. The file uses the default
DELETE rollback journal; no production database is involved.

Before the fix, the initial 10-test set reported 15 subtest/assertion failures and
one lock error. After the fix, all 14 tests passed. A sandbox-only rerun encountered
Windows temporary-directory permission errors; the authorized unrestricted run
passed. An intermediate test-fixture error from patching Flask config descriptors
was corrected to use `patch.dict`; it was not an application regression.

Final full suite: **281 tests passed**. Focused suites: lifecycle 14, active review
workflow 17, reviewer auth 21, field audit 8, serving directions 12, Street View
links 2. No final failures or skips. Python compilation and `git diff --check`
passed. Diff review confirmed unchanged signatures and unchanged SQL semantics;
the larger line count is predominantly indentation under try/finally blocks.

The repository DB hash remained
`d8858055d47af67831b19e9009612a96d78cd7c56bb8a2a97a2c2d11f0172034`.
Final pre-commit review removed the unrelated, unusually named untracked
PowerShell artifact after confirming it contained pager help and had no tracked
project references. No other untracked file was deleted.

The final review restored close-before-response-formatting timing for read
helpers and consensus, and hardened test cleanup if writer setup fails. Running
the file-backed regression with `query_db` loaded directly from `8513f53` again
failed at the independent SELECT after the child reader had exited, confirming
the stranded-lock mechanism. The fixed implementation passes the same test.
If rollback itself fails, that cleanup exception propagates with the original
failure chained; the finally block still attempts close. Exceptions are not
silently swallowed.

## Remaining production risk and recommendation

Three workers can still contend for SQLite's single writer. Long reads, slow
network-backed storage, and existing downstream rebuild transactions can still
produce bounded busy errors; this fix prevents those failures from stranding
connections. It does not make multiworker SQLite contention-free or prove the
original incident had only one cause.

First test the patch on a disposable production-like database with three worker
processes. A short, operator-controlled production trial with three workers is
reasonable before undertaking a PostgreSQL migration, provided the verified
backup, maintenance/rollback procedure, logs and ability to quiesce the app are
ready. Do not leave it serving sustained errors merely to test it. If locks recur,
quiesce and reduce concurrency through the operator/provider while investigating.
Do not enable WAL on network-backed storage. No configuration change was made here.

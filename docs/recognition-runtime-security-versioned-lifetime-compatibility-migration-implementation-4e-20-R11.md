# R11 — versioned lifetime compatibility migration: blocked

## 1. R10 baseline

The approved [R10 design](recognition-runtime-security-versioned-lifetime-compatibility-migration-design-4e-20-R10.md)
defines closed v1/120-second and prospective v2/300-second policies. Existing
authority bytes and historical meaning must remain unchanged. Ordinary issuance
must remain v1. R11 requires stopping if implementation needs a migration decision
not covered by R10.

## 2. Inspected surfaces and changes

Inspected the authority table, lifetime CHECK, scope trigger, canonical validator,
historical clipping, original migration and its final validation in
`runtime_activation_authority_schema.py`; ordinary issuance in
`runtime_activation_authority_issuance.py`; authority/attempt/transition manifest
readers; and `administration_schema.check_control()`.

Only this report is added by R11. No Python, schema, migration, validator,
configuration or test file is changed by this slice. Pre-existing workspace
changes are preserved.

## 3. Concrete migration conflict

R10 section 8 requires a transaction-local TEMP holding table for exact authority
rows, its removal, and complete validation before control commit. The existing
`administration_schema.check_control()` requires:

```python
require(len(conn.execute("PRAGMA database_list").fetchall()) == 1,
        "isolated_admin_control_required")
```

SQLite retains the connection's TEMP database after the last TEMP object is
dropped. Neither savepoint rollback nor full rollback removes that attachment.
`DETACH DATABASE temp` is rejected. Consequently the prescribed staging operation
makes final control validation fail on the same migration connection, even after
all staging objects have been removed.

R10 authorizes selecting exact old/successor authority definitions in the schema
validator. It does not authorize changing this separate connection-isolation
predicate. Closing/reopening the connection would abandon the reserved transaction;
using another connection does not validate the uncommitted successor state.
Skipping final validation or silently allowing TEMP is not an approved correction.

## 4. Existing-row preservation

No repository database was opened or migrated. No authority, lifecycle, attempt,
authentication, approval, binding or audit row was rewritten. Preservation during
the proposed migration has not been established: implementation stopped first.

## 5. Policy enforcement

Current authority definitions still enforce v1 through `LIFETIME`, the v1-only
scope guard and the 120-second table CHECK. Canonical validation remains v1-only.
No successor package or v2 selection has been installed or implemented.

## 6. Historical compatibility

Existing authority, attempt and enrollment-transition historical readers remain
unchanged. R10's successor-to-predecessor manifest projection is not implemented
or claimed validated.

## 7. Credential clipping

Ordinary issuance still takes the minimum of issue time plus 120 seconds and the
original step, confirmation, primary and session deadlines. Historical validation
still reconstructs that original minimum. No credential deadline is extended.
Synthetic v2 clipping tests are not implemented because the migration is blocked.

## 8. Focused diagnostic results

Two direct in-memory SQLite probes were run with the repository virtualenv and
SQLite 3.50.4. They used disposable synthetic data only, without authority issuance,
target access or a recognition lifecycle.

| Probe | Result |
| --- | --- |
| Parent rebuild with populated lifecycle and attempt references, two parent unique keys, `foreign_keys=ON`, deferred NO ACTION checks and TEMP staging | Commit succeeded; foreign-key check empty |
| Before TEMP allocation | `database_list` contained only `main` |
| After dropping the TEMP table | `database_list` still contained `main` and `temp` |
| After savepoint rollback and full rollback | `temp` remained attached |
| Explicit TEMP detach | `OperationalError: cannot detach database temp`, `SQLITE_ERROR` |
| Actual `check_control()` on an in-memory database built from its existing definitions, before TEMP allocation | Passed |
| Same actual validator after creating and dropping one TEMP table | `TrustError: isolated_admin_control_required` |

The small parent-rebuild probe establishes only that particular deferred-FK
behavior. It does not prove the complete authority migration, rollback matrix,
DELETE/WAL interruption, historical compatibility or production safety.

No pytest or lifecycle suite was run: there is no authorized implementation to
validate. Static validation consists of AST parsing of inspected Python surfaces,
this document's whitespace/local-link checks and `git diff --check`.

## 9. Production/default behavior

Implementation is not production migration; migration support is not v2
activation; v2 support is not v2 issuance; and v2 issuance is not production
authorization. None of those actions occurred. The current/default policy remains
v1/120 seconds. No G1, writer, execution, readiness or activation authority is added.

## 10. Decision B

**B — R11 BLOCKED.** R10's required TEMP staging conflicts with the existing
main-only connection invariant during mandatory precommit validation. This is an
observed repository-contract conflict, not a timing or lifecycle finding.

## 11. Required boundary before implementation can resume

A separately approved amendment to R10 must resolve staging versus connection
isolation while preserving the same reserved transaction, full precommit
validation, exact row preservation and rollback. This report authorizes neither
a replacement staging mechanism nor relaxation of the isolation predicate.
R12 is not authorized by this blocked result.

## 12. Explicit production blocks

No production/hosted access, database migration, target DML/DDL, authority issuance,
v2 activation, G1 implementation, Z18, T, broad suite, commit or push occurred.

PRODUCTION AUTHORIZATION: BLOCKED

PRODUCTION EXECUTION: BLOCKED

PRODUCTION ACTIVATION: BLOCKED

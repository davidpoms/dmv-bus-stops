# Runtime-compatible activation owner

The dedicated `runtime_activation` owner supplies the missing v3 lifecycle
bridge. It creates no new authority class and does not change issuer, finalizer,
writer, lifetime-policy or capture configuration.

## Protected lifecycle

The owner acquires a manager-owned control reservation followed by a target
reservation with query-only mode. It validates runtime history, physical/schema
identity, installation, generation, current activation history and owner scope.
Only registered activation views can use the new runtime-readiness adapter.
Readiness uses the existing version-aware proposal/ACK/approval and dependency
readers plus current claim disposition. Legacy readiness is never substituted.

Authentication reuses the existing primary/session, profile binding, MFA seed,
counter, expiry and denial kernels. Before and after activation, login is through
the existing trusted login hook. MFA enrollment/session routes retain their
existing credential requirements. Installations without activation storage retain
the original pre-activation authentication backend; no failed validation falls
back to another backend.

An explicit step-up binds the action, authenticated session, installation and
generation. Preparation writes the existing one-use confirmation with the exact
target and readiness/activation ceremony digest. Consumption revalidates runtime
readiness and compares that digest before the existing activation append. Only
`NOT_ACTIVATED -> ACTIVATED` is admitted by this bridge. Suspension and
deactivation use the existing transition map and require a new action-specific
MFA step-up; they remain possible without ready-to-execute dependencies.

Activation/suspension/deactivation and invalidation of all old primaries,
sessions, step-ups and confirmations share one control commit. The target stays
reserved and query-only through resolution. Final checks repeat identity,
activation, clock, registered MFA epoch, credential/step-up expiry and zero target
changes. Public results contain data only, never a context or execution handoff.
Fresh post-transition authentication is a separate ceremony, not automatic
credential renewal. Suspended/deactivated installations support owner login and
inspection, but cannot use this path to reactivate.

## Durable failure outcomes

| Boundary | Durable outcome | Owner action |
| --- | --- | --- |
| Failure or death before control commit | No activation or credential-fence transition commits | Stop and inspect; no automatic retry |
| Confirmed control commit | Activation and credential invalidation both commit | Fresh sign-in and protected readback |
| Death/lost response immediately after commit | Same committed state; no result or process-local handoff is needed | Fresh sign-in and protected readback; do not resubmit |
| Uncertain commit or cleanup | No usable result is published; durable state is authoritative | Inspect through fresh authentication; keep service stopped if inspection fails |
| Post-activation authentication failure | Committed activation remains; no rollback or replacement authority is inferred | Correct owner authentication or keep service offline; never edit the ledger |

The owner never writes target data, commits the target, creates an execution
claim, issues authority, or changes schema. Shutdown cannot recreate an old
continuation. A blocked or uncertain readback is not permission to retry.

## HTTP and owner interface

All paths are under `/api/admin/recognition-control` and preserve the existing
owner browser session, CSRF checks, no-store responses and sanitized errors.

| Path | Meaning |
| --- | --- |
| `GET /owner-activation` | Owner browser page; no transition |
| `GET /runtime-activation` | Authenticated durable activation readback |
| `GET /runtime-activation/readiness` | Fresh runtime readiness; never changes activation |
| `POST /runtime-activation/step-up` | Exact action/installation/generation MFA step-up |
| `POST /runtime-activation/confirmations` | Prepare activation confirmation only |
| `POST /runtime-activation` | Owner-managed activate/suspend/deactivate transition |

Legacy routes remain unchanged. Installation deactivation does not forge an
issuer-specific governance revocation. Existing signed issuer revocation and
outcome-inspection rules remain in force.

Owner steps: [activation and suspension](recognition-runtime-owner-activation-procedure.md).
Rollback: [owner rollback](recognition-runtime-production-rollback-procedure.md).
This source update requires a separately reviewed deployment artifact; it does
not match or silently replace the historical R30 archive/hash manifest.

## Validation

Focused activation/HTTP/crash/restart run: **17 passed, 5 subtests passed**.
Final confirmation-expiry and positive-lifecycle checks: **2 passed**, including
the additional confirmation-cannot-outlive-step case (18 distinct focused cases
covered overall). The creation-second race found during validation was corrected
by preserving the existing authentication kernel's exact issuance timestamp in
its profile-binding row; the second-boundary regression passed.

Existing authentication and R28/R30-related regression group: **107 passed,
146 subtests passed**. Coverage includes finalization/integration, lifetime
policies, history, bounded harness, outcome journal, schema lineage, late journal
migration, and production-topology provisioning fixtures. These use disposable
files and synthetic approvals; no production lifecycle is run.

Python AST, Jinja template compilation, whitespace/local-document-link checks
and `git diff --check` passed. All 85 unchanged modules in the historical
88-module R30 source manifest retain their byte hashes; only the three intended
existing modules differ, plus the new owner and template. Schema/lineage,
lifetime, issuer/finalizer, writer and capture configuration remain unchanged.
The historical release archive/hash manifest is intact and is not the deployment
artifact for this fix. No broad/full suite, production or hosted access,
production migration, commit or push.

PRODUCTION AUTHORIZATION: GRANTED
PRODUCTION EXECUTION: BLOCKED
PRODUCTION ACTIVATION: BLOCKED

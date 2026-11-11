# 4e-20-R30 - production authorization and deployment decision

## 1. R29 readiness basis

**B - AUTHORIZE DEPLOYMENT, BUT NOT ACTIVATION.** The project owner's R30
instruction authorizes this scoped decision. The reviewed implementation may be
deployed within the constraints below. Production recognition activation and
execution remain blocked pending an explicit activation decision confirming the
actual deployment inputs already required by R29. No new architecture stage is
created.

[R29](recognition-runtime-security-final-production-readiness-review-4e-20-R29.md)
actually concludes **READY FOR EXPLICIT PRODUCTION AUTHORIZATION**. It identifies
no unresolved implementation blocker or R21-B violation. It also expressly
records that actual owner/target bindings, protected public root, approval
custodians and rollback actor were synthetic in the tests and must be confirmed
for production authorization. This decision does not invent those identities or
claim to have verified a live deployment.

The implementation evidence remains
[R28](recognition-runtime-security-production-integration-4e-20-R28.md): 88 focused
tests and 96 subtests passed, owner interruption/revocation/duplicate inspection
passed, and exactly one clean isolated production-like owner lifecycle reached
COMPLETED with verified target effect/witness and 141 seconds remaining. These
results establish readiness, not an actual production appointment or activation.

## 2. Final security baseline

Read-only SHA256 comparison found **no mismatches in 21 recorded files**: the 16
R28 source/test entries in `.tmp/recognition-r28-final-source-hashes.json`, plus
the non-replaced R26 compatibility entries in
`.tmp/recognition-r26-fix-source-hashes.json`. For files intentionally changed
and revalidated by R28, the final R28 digest takes precedence. This confirms the
local deployment candidate, not an already-deployed production installation;
production has not been accessed.

The deployment artifact must contain those exact validated implementations and
their reviewed dependencies. An unvalidated runtime change is outside this
authorization. Existing unrelated working-tree changes do not gain approval
merely because they are present; the deployer must use the reviewed recognition
change set rather than treating the whole dirty workspace as a release.

The unchanged
[R21-B](recognition-runtime-security-consolidated-finalization-contract-4e-20-R21-B.md)
baseline is mandatory:

| Boundary | Preserved enforcement |
| --- | --- |
| Issuer/finalizer | Separate exact governance decisions, original source eligibility and protected original-holder finalization |
| Decision/target/action/write set | Same immutable D, exact operation and physical target, fixed family action and manifest/write-set digest |
| Original holder | Genuine context/attempt/entry registry, original credentials, PID/live Thread and owned reservation/connection lifetime |
| Validity | Closed policy/version mapping, credential/consent clipping, monotonic-consistent time and expiry at required boundaries |
| Freshness | Live authentication, activation, approval/proposal/ACK, dependencies, readiness, stop, physical identity, history/claim/control and reservation validation |
| Duplicate/concurrency/revocation | Durable decision exclusions and sole pending, original-use fences, foreign-thread poisoning and ordered exact-scope revocation |
| Target proof | Complete family effects and witness in one atomic target transaction, actual row evidence and postcommit independent verification |
| Outcome/uncertainty | Same-D durable outcome; separate control/target commits; no usable success on uncertain commit/cleanup and no executable retry |

## 3. Exact deployment scope

| Action | Decision and limits |
| --- | --- |
| A. Production code deployment | Authorized for the reviewed recognition implementation, with compatible inspection readers and existing gates retained. Identify the exact release artifact and its validated source hashes before installing it. No unrelated application changes are included. |
| B. Required schema/journal installation | Authorized only for missing reviewed packages through their existing exact migration owners: verified predecessors/backups, inactive state, control reservation then target reservation, complete lineage checks and W/Y schema/profile transitions. No generic SQL, arbitrary predecessor, journal bootstrap against enrolled data or historical hash rewriting. |
| C. Trust-root/approval provisioning | Authorized only through the R28 mechanism: independently attributable installation-owner input, protected deployment-installed public root and exact signed subject approvals, followed by current authenticated owner verification. No root/key/identity is designated by this document, no private key is read here, and synthetic test configuration must not be copied. |
| D. Production policy configuration | Preserve v1/120 ordinary/default and the existing prospective/test-only v2/300 restriction. Installing compatibility storage does not activate v2 or reinterpret v1. No production source-lifetime selection change is authorized. |
| E. Production recognition activation | NOT AUTHORIZED. No production issuer appointment for executing an operation, real source issuance or recognition lifecycle may be inferred from code/schema/configuration deployment approval. |

Schema and configuration operations remain conditional on their existing exact
identity/approval prerequisites. If the actual installation, owner, signer
custody or approved subject is missing or mismatched, that operation must not
proceed. This is not permission to choose an arbitrary target or substitute a
caller-created public root. The actual production deployment manifest and
custodians have not been supplied in this conversation; no names, database paths
or key fingerprints are fabricated here.

## 4. Lifetime policy

**v1 = 120 seconds. v2 = 300 seconds.** Neither changes. v1 remains ordinary/default
production policy; v2 remains prospective/test-only under this deployment-only
decision. Existing authority history keeps its own immutable policy.

The isolated v2 success does not prove v1 or v2 meets every production workload,
and it does not authorize automatic lifetime selection, renewal or an unrestricted
configuration knob. The test-only pre-persistence v2 adapter is not deployment
code. There is no 600-second source-authority policy. Administrative/governance
freshness intervals do not alter these source lifetimes.

## 5. Production authority scope

Only `authority.provision_production_authority` through the fixed
`runtime_production_governance` verifier is within deployment scope. Its public
trust input is `<control filename>.governance-root.json` for the actual approved
installation/owner, protected under R21-B's deployment/OS trust boundary.

Closed signed approvals retain exact subject, policy, holder credentials,
installation binding, target/control physical identities and clipped bounded
expiry. Fresh owner authentication/MFA, distinct approval audit linkage and
prospective entitlement/consumption/revocation remain required. Provisioning is
not permission to bypass any production activation gate.

No general authority, broader target, transferable handle, re-delegation,
renewal, retry authorization or recovery-based reauthorization is granted. No
new runtime authority is introduced. G1 does not continue automatically.

## 6. Safe deployment order

1. Identify the reviewed release artifact and actual installation/owner scope;
   record an authorized deployment operator and rollback custodian. Preserve the
   current inactive state and verified database backups. Missing identity or
   permissions means stop, not inference from project ownership alone.
2. Deploy the validated code with all existing gates closed and compatible
   durable inspection available. Verify the installed artifact matches the
   approved source baseline before any schema operation.
3. Install/verify only required exact schema and journal lineage. Where signed
   migration approval needs the public trust input, install and verify that
   prerequisite before invoking the migration; the numbered plan does not
   override this real dependency. Retain reservation ordering, predecessor
   validation, verified backups and W/Y profile enrollment.
4. Complete/verify protected production trust-root and exact approval
   configuration against actual deployment identities and signer custody.
   Verify current configuration, schema/fingerprint/profile, policy, inspection
   and revocation paths without issuing execution authority.
5. **STOP before activation.** Supply the actual deployment bindings and
   custodians for a short explicit activation decision under R30. Preserve v1/v2
   restrictions; any proposed prospective production policy selection must be
   stated expressly rather than inferred from the successful test.
6. Only if activation is subsequently explicitly authorized, perform controlled
   activation under the existing owner/gates and observe the first separately
   permitted production operation. This step is not authorized by this decision.
7. Retain the exact source D, decision/pending, target witness/effect evidence,
   control outcome, revocation and audit/lineage evidence. An incomplete or
   uncertain outcome never permits another target execution.

No step is executed automatically by R30. This document records authorization
scope, not a claim that deployment or configuration verification has occurred.

## 7. Rollback and incident plan

The R29 plan is confirmed. The project owner retains the governance decision
over rollback; the actual operator must be designated and independently possess
the existing exact deployment/revocation permissions before acting. No unnamed
runtime or source issuer obtains rollback powers from this document.

Stop new ceremonies/activation and use existing authenticated revocation controls
within their current scope. Preserve target/control databases, backups, lineage,
audit, decision exclusions, witnesses and outcome inspection. Keep compatible
readers; do not install an older binary unable to read the installed journal.

For an uncertain commit, inspect the original D and recompute actual target
proof. A committed effect with pending control remains a committed target fact;
no retry, automatic repair or recreated handoff is authorized. Missing witness
alone is not proof of rollback. Never drop fences/history or restore only one
database to an older state to make the effect executable again. Halt and retain
evidence if rollback compatibility or outcome is uncertain.

The reviewed split target/control outcome semantics are preserved: deployment
does not promise cross-database atomicity, nor authorize availability repair by
re-execution. Activation remains withheld until the actual deployment's owner
expressly confirms these operating conditions with its bindings/custodians.

## 8. Authorization decision

**B - AUTHORIZE DEPLOYMENT, BUT NOT ACTIVATION.**

There is no new implementation or architecture blocker. The distinction is the
explicit R29 deployment-input condition: this request supplies no actual owner/
target trust binding, signer/approval custody or named operational rollback
custodian. The isolated approvals cannot establish those live facts. It would
therefore be inaccurate to record unconditional activation authorization.

This decision approves only the bounded code/schema/configuration deployment
scope in section 3, subject to its existing exact approval prerequisites.
Recognition activation and execution remain blocked. No R31 or new design
review is created.

## 9. Execution boundary and validation

R30 creates only this document. No production connection, migration, authority,
appointment, permission change, activation or recognition execution occurs.
No runtime code, schema, lifetime or production configuration is modified.
No lifecycle or pytest is run. No commit or push is performed.

Read-only baseline hash verification found no mismatch. Established document
whitespace/local-link checks and `git diff --check` are the only validation
commands beyond evidence inspection.

## 10. Next operational step

Prepare the exact deployment artifact and actual installation-owner/public-root/
approval/rollback-custodian record. Execute deployment only when separately
instructed and its existing prerequisites are met. Return to the **R30 explicit
activation decision**, with those concrete inputs, before activation or any
real operation. Do not reopen architecture or repeat the lifecycle campaign.

**PRODUCTION AUTHORIZATION: GRANTED FOR DEPLOYMENT ONLY**
**PRODUCTION EXECUTION: BLOCKED**
**PRODUCTION ACTIVATION: BLOCKED**

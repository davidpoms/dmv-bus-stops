# Project-owner production activation checklist

Complete before any production execution. Based on the
[R30 decision](recognition-runtime-security-production-authorization-decision-4e-20-R30.md)
and [deployment-preparation runbook](recognition-runtime-security-production-deployment-preparation.md).
This checklist is not activation approval and creates no runtime authority.

All boxes remain unchecked. Supply actual values and attributable confirmations;
do not substitute test/developer identities or disposable configuration. Record
only public identifiers, fingerprints, evidence references and approval records,
never private keys, tokens, credentials or MFA material. Named roles may overlap
only where the existing approved separation rules permit.

“Codex can verify” means possible checks of explicitly supplied local/offline
evidence under a subsequent instruction. No production access, provisioning,
activation, execution or new verification run is performed by this checklist.
Mechanical consistency does not establish a person's mandate or approval.

## Expected artifact

- Package: `recognition-r28-source.zip`, the source-only recognition overlay.
- Expected ZIP SHA256: `d1eb8ddc0dddae3dc1e4cbd26221dc0b859ba6ca3a141b69e079ddeaa3391e59`.
- Expected manifest SHA256: `1ff86e5711893df4d54e4610496c12ee98697440e50fe96d23c9ddac64f713fd`.
- [Package, manifest and checksum location](recognition-runtime-security-production-deployment-preparation.md#prepared-artifact-and-verification).
- These are recorded expected hashes, not a new attestation of installed production bytes.

## Owner completion record

For each row, record the supplied value/evidence, confirmer's actual identity,
confirmation date/time with timezone, and approval/evidence reference. A blank,
ambiguous, stale or mismatched item means **STOP**.

| Item | Value/evidence to supply | Who must confirm | What Codex can mechanically verify from supplied evidence | What requires human confirmation |
| --- | --- | --- | --- | --- |
| [ ] Production environment/target | Actual environment, installation/target/owner identifiers, physical deployment identity, current profile/generation/incarnation | Project owner and authorized installation owner | Compare identifiers across configuration, binding/profile and approval records | This is the intended authorized production environment, not a test target |
| [ ] Deployment artifact/hash | Exact retained package and manifest, release/handoff location, installed-file verification record; expected hashes above | Deployment operator; project owner accepts release scope | Hash package/manifest, compare member hashes and approved baseline, check dependency references | Approved custody/handoff and installation of this release; no unrelated changes included |
| [ ] Production database/journal target | Actual approved target/control paths and identities, journal locations, fingerprints and backup references | Installation owner and database/deployment custodian | Compare sanitized database/schema identity records, fingerprints and journal bindings | These are the correct live databases, with approved access and backups |
| [ ] Trust root/public verification material | Actual public key and fingerprint, mandate/installation/owner binding, protected root destination and custody reference | Governance owner and signing/trust-root custodian | Check public encoding, canonical fields, fingerprints and signatures against the supplied pinned public root | Authenticity of the root's provenance, authorized signer custody and protected installation/replacement |
| [ ] Authorized production custodians | Named governance/installation owner, signer, constrained issuer holder and other operators below; authority/scope references | Project owner; each custodian acknowledges responsibility | Compare named identities, scopes and references for internal consistency | Actual authority, acceptance of responsibility and compliance with approved separation rules |
| [ ] Issuer/provisioning binding | Actual original holder, installation/target/profile scope, exact policy/action/write-set intent and appointment/approval references | Governance/installation owner and authorized issuer holder | Compare exact signed subjects and digests with R28 provisioning/issuer requirements | Appointment is authorized and prospective; credentials belong to that original holder; no self-appointment or broader rights |
| [ ] Approval registry binding | Evidence that actual exact signed approvals bind the original owner/session and target/control scope through the fixed production verifier | Authorized provisioning operator and governance owner | Check sanitized approval/provenance bindings, expiry and policy/subject consistency | Actual authenticated process-local registration occurred through the approved mechanism; no copied disposable registry or relabelled handle |
| [ ] Schema/journal lineage | Installed package identities, ordered audit/manifest hashes, predecessor/current schema evidence and completed W/Y profile transition where required | Database/deployment custodian and installation owner | Compare exact package definitions/hashes, ordered lineage and preserved historical references | Evidence describes the actual deployment; required migrations completed under the approved owners, with no pending/uncertain transition |
| [ ] Deployment operator | Actual identity, exact installation scope and existing deployment permissions | Project owner and operator | Compare scope with the approved release and deployment record | Operator is designated, authorized and available; designation grants no new runtime permissions |
| [ ] Activation operator | Actual identity, existing activation permissions and exact activation scope | Project owner and installation owner; operator acknowledges | Compare identity/scope with the eventual activation approval | Operator is explicitly designated and permitted to activate only after approval |
| [ ] Emergency revocation operator | Actual identity, existing revocation authority, contact/escalation route and exact scope | Governance/installation owner; operator acknowledges | Check supplied permission/approval references and scope consistency | Operator can be reached and is authorized to stop/revoke under existing controls |
| [ ] Deployment window | Start/end with timezone, maintenance coordination and stop/escalation conditions | Project owner, deployment and activation operators | Check timestamps/order and overlap with supplied approval validity | Window, availability and operational impact are accepted; it does not extend authority expiry |
| [ ] Rollback owner | Actual identity, existing rollback/revocation permissions and escalation responsibility | Project owner; rollback owner acknowledges | Compare responsibility and permission references with the rollback plan | Owner is authorized, available and accepts the no-retry/uncertain-outcome procedure |
| [ ] Rollback verification | Paired backup identities/checksums, integrity evidence, compatible rollback/inspection artifact and exact-D incident procedure | Rollback owner and database/deployment custodian | Compare checksums, integrity records, schema/reader compatibility and evidence linkage | Backups are retained and usable; rollback preserves outcomes/fences and never replays a committed effect or restores only one database to erase it |
| [ ] Activation approval | Explicit owner decision, approval identity/time, exact environment/artifact/bindings, permitted operations/action scope, operators, window and policy restrictions | Project owner; activation operator verifies before acting | Cross-check approval scope against every confirmed row and detect missing/conflicting terms | Owner expressly authorizes activation; deployment approval alone is insufficient, and any execution still needs its own valid runtime authority |

## Final owner gate

- [ ] Every row has actual values, a named authorized confirmer and attributable evidence; discrepancies are resolved without substituting test data.
- [ ] Preserve v1 = 120 seconds, ordinary/default; v2 = 300 seconds, prospective/test-only under current R30. No implicit v2 production selection, test adapter, new lifetime or deadline extension.
- [ ] Accept separate target/control commits: a target effect plus witness may be committed while control remains pending. Preserve exact-D inspection, revocation, historical lineage and permanent duplicate fencing. Uncertainty never authorizes another target execution.
- [ ] Confirm the explicit activation decision under R30 before any activation. Checklist completion alone neither activates production nor issues an authority. Any missing prerequisite keeps activation and execution blocked.

No code, schema, policy, permissions or deployment artifact was changed. No
production access or execution, commit or push occurred in preparing this document.

PRODUCTION AUTHORIZATION: GRANTED FOR DEPLOYMENT
PRODUCTION EXECUTION: BLOCKED
PRODUCTION ACTIVATION: BLOCKED

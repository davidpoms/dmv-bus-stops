# Closed generation-5 runtime device successor

This operation is local implementation tooling, not permission to run production
maintenance. It supports only the source binding
`055d7f03d6dae4157d067e086a17a5b3f6baecb461cf4f4fbd7c1f6e7634cb0b`
and profile `6ee02a54dce497afe4f6d0185f614ac0229b41a5831ab71b9f5e3c6cf72e6560`.
Both runtime devices change from 57 to 49, generation 5 becomes 6, and the host,
paths, inodes, target schema, installation, owner and target remain unchanged.
It rejects completed foundation, any earlier activation, other control topology,
pending schema transition, work/claims/authority/recovery, unsafe files and an
active/uninitialized emergency stop. Both databases must already use DELETE/FULL.

> This authorization accepts unresolved storage-continuity uncertainty for the exact approved device transition. It does not establish physical continuity or authorize arbitrary filesystem changes.

There is no device tolerance. A later 49-to-63 observation fails normally. G5
bindings/profiles/audits remain immutable, MFA enrollment and epoch remain intact,
and primary/admin proofs, step-ups, confirmations and approvals are invalidated.
No activation or execution authority is granted.

## Storage and authorization

No DDL, new table, guard change or schema migration is required. A genuine fresh
600-second challenge uses the existing table and deferred profile/binding/audit
relationships. Its distinct audit action is
`runtime_profile_successor_challenge_issued`; completion uses
`runtime_profile_device_successor_committed`. Initial enrollment and schema
transition provenance remain separate from this signed successor branch.

The existing offline Ed25519 custodian key signs the existing canonical
`{serialized_approval, signature}` envelope. Only the new successor purposes use
`holder={kind:governance_custodian,actor_id:<root owner>}`. This holder cannot enter
ordinary governance, runtime authentication, foundation or execution APIs.
Never invent session hashes. No private signing key goes to the hosted service.

The maintenance operations are POST requests under
`/api/admin/recognition-control/runtime-profile-successor/`:

| Operation | Exact JSON fields | Effect |
| --- | --- | --- |
| describe | authorization | Signed inspection; read-only actual-worker scope |
| prepare | authorization | Signed preparation; commits challenge/audit, collects private WSGI evidence |
| plan | authorization, review, backups | Signed inspection; deterministic read-only plan |
| complete | authorization, nonce | Signed exact-plan completion; atomic control-only succession |
| inspect | authorization | Signed inspection; read-only durable outcome |

`authorization` is the parsed envelope. `review` is the existing prepared review
object. `backups` contains absolute `target` and `control` backup paths. `nonce`
is the one-time value returned by preparation, never a URL argument or log field.
All operations execute in the real WSGI request, not a console test client.
Responses are no-store. Signature authentication is independent of browser
cookies; existing browser authentication and CSRF routes are unchanged.

## Operator procedure after separate deployment approval

Freeze/test/deploy the final code first. Do not qualify during development or
diagnostic instrumentation: qualification fingerprints include runtime_validation.
The steps below are a procedure, not commands executed by the implementation.

1. Before issuing any challenge, stage the HTTP client, private output paths,
   public-root copy, log access, review command and offline signing/transfer path
   described below. Establish a quiescent maintenance window for ALL target/control
   writers. Create/verify the target backup first using SQLite backup APIs; it may
   be reused only while its schema/typed contents still match the reserved source.
   Do not create the control backup yet: it must include preparation.
   Then choose one fresh authorization UUID. On the offline custodian machine build
   an inspection payload using the installed public root's matching public JSON:

   ```text
   python scripts/operator/recognition_governance.py successor-payload --public-root <PUBLIC_ROOT> --purpose inspect --authorization-id <UUID> --output <INSPECT_PAYLOAD>
   python scripts/operator/recognition_governance.py sign --private-key <EXISTING_ENCRYPTED_KEY_OUTSIDE_REPOSITORY> --public-root <PUBLIC_ROOT> --payload <INSPECT_PAYLOAD> --output <INSPECT_ENVELOPE> --confirm-offline
   ```

2. Submit the inspection envelope to `describe` through the live application.
   Preserve its scope response privately. This operation is read-only; it does
   not require Owner Activation to render. Review the exact source/destination,
   owner, epochs, schema/control hashes, stop state and uncertainty acknowledgement.

3. Build and sign preparation from that response:

   ```text
   python scripts/operator/recognition_governance.py successor-payload --public-root <PUBLIC_ROOT> --purpose prepare --authorization-id <UUID> --source <DESCRIBE_RESPONSE> --operator <OPERATOR> --reason <REASON> --output <PREPARE_PAYLOAD>
   python scripts/operator/recognition_governance.py sign --private-key <EXISTING_ENCRYPTED_KEY_OUTSIDE_REPOSITORY> --public-root <PUBLIC_ROOT> --payload <PREPARE_PAYLOAD> --output <PREPARE_ENVELOPE> --confirm-offline
   ```

4. POST `prepare`. Retain its nonce privately in memory. Do not log, store in
   source control, or put it in WSGI configuration. Preparation is state-changing.
   The collector records `RECOGNITION_RUNTIME_EVIDENCE` in the existing private
   application error log; do not use startup logs as evidence. Review the fresh
   record independently and use `prepare_recognition_runtime_review.py` with its
   existing documented arguments. Do not fabricate observations.

5. Within the challenge lifetime create/verify the control backup using SQLite
   backup APIs under the same quiescent window. Pair it with the staged target
   backup. The control copy must include preparation; both copies must exactly
   match the reserved live stores at planning/consumption.
   Do not use filesystem copies of open databases. POST `plan` using a fresh signed
   inspection envelope, the reviewed evidence and backup paths. Review its plan
   digest. Repeated planning with the same inputs is read-only and deterministic.

6. Build/sign completion from that plan response:

   ```text
   python scripts/operator/recognition_governance.py successor-payload --public-root <PUBLIC_ROOT> --purpose complete --authorization-id <UUID> --source <PLAN_RESPONSE> --output <COMPLETE_PAYLOAD>
   python scripts/operator/recognition_governance.py sign --private-key <EXISTING_ENCRYPTED_KEY_OUTSIDE_REPOSITORY> --public-root <PUBLIC_ROOT> --payload <COMPLETE_PAYLOAD> --output <COMPLETE_ENVELOPE> --confirm-offline
   ```

7. POST `complete` with that envelope and the nonce. The server revalidates the
   signed plan, source, backups, physical identity and time under control/target
   reservations. It commits only control data. Success reports COMMITTED,
   generation 6, destination binding/profile hashes and execution_authority=false.

8. POST `inspect` with a fresh signed inspection envelope. Outcomes are
   NOT_PREPARED, PREPARED, EXPIRED_UNCONSUMED, COMMITTED or INCONSISTENT. A lost
   response requires inspection, never blind retry. An expired unused challenge
   stays historical; a new UUID/signature/observation is required to try again.
   If evidence collection fails after preparation commits, inspect and wait for
   expiry rather than manufacturing/reusing a nonce or observation.

Preparation and completion are the only mutations. There is no unsigned HTTP
authority, generic force option or console identity substitution. Do not attempt
to meet deadlines by changing the lifetime. If the offline review/signing/backup
workflow cannot finish in 600 seconds, stop and report that operational blocker.

## Explicit request and evidence steps

These are operator-run templates after approval, NOT operations performed by this
release. Replace bracketed paths with real absolute paths in private storage.
Do not run the network client on the offline private-key machine. Transfer only
public payloads/envelopes between the online operator and offline signer. Never
transfer the nonce or private key to the other machine.

In an interactive Python terminal on the online operator machine, stage this
standard-library client BEFORE preparing the challenge. Do not run it through a
captured/recorded terminal, print `prepared`, or enable HTTP body logging:

```python
import json, os, urllib.request
from pathlib import Path

BASE = 'https://davidpoms.pythonanywhere.com/api/admin/recognition-control/runtime-profile-successor/'
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None
opener = urllib.request.build_opener(NoRedirect)
def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))
def save_new(path, value):
    # Use an existing private directory; never overwrite an artifact.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, sort_keys=True, separators=(',', ':'))
def post(operation, envelope_path, **extra):
    request = urllib.request.Request(BASE + operation,
        data=json.dumps(dict(authorization=read_json(envelope_path), **extra)).encode('utf-8'),
        headers={'Content-Type': 'application/json', 'Accept': 'application/json'}, method='POST')
    with opener.open(request, timeout=60) as response:
        return json.load(response)
```

Each call below is a SEPARATE explicit operator action at the corresponding
numbered stage above. Do not paste/run them all at once. A transport timeout does
not establish rollback. Never automatically retry `prepare` or `complete`:

```python
# Stage 2: inspection envelope uses this attempt's UUID.
scope_response = post('describe', '<INSPECT_ENVELOPE>')
save_new('<DESCRIBE_RESPONSE>', scope_response)
# Transfer DESCRIBE_RESPONSE to the offline signer; build/sign preparation.

# Stage 4: exactly once. The nonce stays in this terminal's memory.
prepared = post('prepare', '<PREPARE_ENVELOPE>')
print(prepared['authorization_id'], prepared['challenge']['challenge_id'],
      prepared['challenge']['challenge_sha256'], prepared['challenge']['expires_at'])

# Stage 5: only after real evidence review and the coherent backup pair.
plan_response = post('plan', '<FRESH_INSPECT_ENVELOPE>',
    review=read_json('<REVIEW_FILE>'),
    backups={'target': '<PA_TARGET_BACKUP>', 'control': '<PA_CONTROL_BACKUP>'})
save_new('<PLAN_RESPONSE>', plan_response)
print(plan_response['plan_sha256'], plan_response['plan']['deadline_at_utc'])
# Transfer PLAN_RESPONSE to the offline signer; build/sign completion.

# Stage 7: exactly once, with the separately signed exact plan.
completed = post('complete', '<COMPLETE_ENVELOPE>', nonce=prepared['nonce'])
print(completed['state'], completed['generation'], completed['binding_sha256'],
      completed['profile_sha256'], completed['execution_authority'])

# Stage 8, or after ANY uncertain prepare/complete outcome; never auto-retry.
outcome = post('inspect', '<FRESH_INSPECT_ENVELOPE>')
print(outcome)
```

If preparation times out before returning its nonce, inspect by the signed
authorization UUID. If PREPARED, wait for expiry and start a fresh authorized
attempt; the nonce cannot be recovered from its stored hash. Inspection validates
the entire durable history even if a commit action is missing/renamed. INCONSISTENT
requires investigation and never authorizes repair/retry.

On PA Bash, extract this challenge's existing private log envelope into a NEW
private file. Set CHALLENGE_ID, CHALLENGE_SHA256 and the two absolute artifact
paths from this attempt; do not include other challenges or rejected records.
Review all matching records, not only a convenient worker:

```bash
umask 077
set -o noclobber
set -o pipefail
if grep -F 'RECOGNITION_RUNTIME_EVIDENCE ' /var/log/davidpoms.pythonanywhere.com.error.log |
  grep -F "\"challenge_id\":\"$CHALLENGE_ID\"" > "$PRIVATE_LOG_EXCERPT"; then
  python scripts/active/prepare_recognition_runtime_review.py \
    --private-log "$PRIVATE_LOG_EXCERPT" \
    --challenge-id "$CHALLENGE_ID" --challenge-sha256 "$CHALLENGE_SHA256" \
    --expected-generation 5 \
    --source-binding-sha256 055d7f03d6dae4157d067e086a17a5b3f6baecb461cf4f4fbd7c1f6e7634cb0b \
    --output "$REVIEW_FILE"
else
  echo 'STOP: log extraction failed or no matching runtime evidence; do not use an existing excerpt'
fi
```

If more than one observation exists, the existing tool requires the reviewed
`--selected-observation-sha256`; disagreement still rejects. Transfer only the
review artifact to the online client. This console step packages worker logs;
it does NOT collect a console observation or enroll a profile. Honor a missing,
malformed, stale or disagreeing record as a stop condition.

## Timing preflight and stop conditions

The server starts the 600-second challenge at preparation, not when the response
arrives. Integrity checks/collection, HTTP time, log retrieval, control backup,
review, transfers, plan validation, signing and final validation consume that same
window. The completion envelope may impose an EARLIER deadline. Inspection
envelopes have their own expiry and may need fresh signing; they never extend the
challenge.

Before a production attempt, measure the real target-backup step outside the
challenge and establish a conservative budget for the control backup, two-way
artifact transfers, review, signing and HTTP operations. Pre-stage script bodies,
paths and operator access, never signatures/observations for a future challenge.
Reserve enough time for full server-side backup/content/history revalidation at
completion; do not send a request merely because seconds remain on the clock.
Any changed source audit head, application write, changed backup, clock anomaly
or expiry requires stopping, not adjusting digests or reusing the plan.

No production sizes, throughput or operator transfer/signing timings have been
measured by these local tests. Therefore the real 600-second feasibility is
UNVERIFIED: production remains NO-GO until a timed operational preflight shows
adequate margin. If it does not fit, the smallest next step is to improve staging
and keep target writers quiescent so the target backup can precede preparation;
do not extend lifetimes or create another recovery architecture.

## After G6

Fresh owner primary login and MFA administrative authentication are required.
Create fresh qualification backups/evidence in the enrolled serving context, then
record focused qualification against G6. The CLI supports expected-generation 6
only when its runtime lineage is validated; a differently identified console still
cannot substitute for the WSGI worker. Rehearsal and old claim recovery remain G5-only.

Use existing Foundation Preview, exact-plan offline signing, completion, durable
status, readiness, MFA step-up, confirmation and activation. G6 eligibility is
derived from verified successor provenance; it is not generation>=5. All ordinary
operation approvals, execution authority, claims, recovery and writer checks remain.

## Failure and rollback

Only control changes, so one SQLite transaction commits profile, binding,
revocation and audit. Target remains query-only and its reservation is retained
through control commit. Integrity probes use separate read-only connections so
SQLite temp-schema creation cannot relax isolated-control validation. No journal
mode is switched. This does not certify NFS host-crash durability or prevent a
privileged host operator from replacing files outside SQLite reservations.

Failure before commit rolls back the entire successor; the preparation can remain
usable until expiry if its scope and backups remain unchanged. After commit there
is no delete/undo command. INCONSISTENT never repairs anything. A paired restore
or any later identity transition is a separately reviewed recovery operation.

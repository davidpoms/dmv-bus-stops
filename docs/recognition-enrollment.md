# Authenticated target enrollment contract (Slice 5)

LOCAL/SYNTHETIC only. No production authority, execution, enrollment registry,
storage attestation, signing key, automatic migration or production activation is
provided. Production provisioning still rejects. Existing recognition writers,
Explorer and First Look lifecycle remain unchanged.

## Repository findings before implementation

- The web deployment selects an existing absolute `DMV_BUS_STOPS_DB` through
  `src/api/deployment.py`; configuration is not enrollment. Recognition's
  `schema.connection()` uses explicit `mode=ro`/`mode=rw`, enables foreign keys,
  and does not create a missing target.
- Existing `authorization.target_identity()` observes hostname, resolved main-file
  path, device/inode and rejects attached non-main/temp databases. This is useful
  identity evidence, not authenticated storage continuity.
- The local test interpreter links SQLite **3.50.4**. No production SQLite version
  or database was queried. The repository does not establish one enforced global
  application schema number. Recognition schemas instead compare actual expected
  SQL definitions; physical-stop history also carries migration/version records.
- The application does not mandate WAL or enable it through recognition. Repository
  tests exercise WAL snapshot behavior; offline rehearsal tools may reject WAL.
  `docs/sqlite-lifecycle-hotfix.md` explicitly avoids enabling WAL as a workaround.
- `scripts/active/backup_database.py` uses SQLite online backup. The deployment
  runbook notes that a correct backup may have a different file SHA from its source.
  `docs/DEPLOY_LIMITED_PILOT.md` restores to a new explicit path with traffic stopped;
  `docs/physical-stop-identity-v2.md` also documents controlled file replacement.
- Existing `docs/recognition-authorization-hardening.md` requires independent
  enrollment and says replacement/restore/relocation retires enrollment. It explicitly
  acknowledges that device/inode cannot detect every in-place restore or inode reuse.

These findings rule out a whole-file hash as live target identity: normal data
writes, WAL state, checkpointing and backup layout can change bytes without changing
the logical target. Database contents or an in-database UUID can themselves be
restored and cannot independently attest storage continuity.

## Target identity and the unavoidable external dependency

The contract binds:

- Existing hostname/path/device/inode observation of the regular main SQLite file.
- Canonical parent path and parent device/inode; one hard link is required.
- Independently supplied protected host/deployment identities.
- An independent storage `incarnation_id` which must change for restore/replacement.
- Exact schema digest: canonical sorted non-internal SQLite schema objects
  `(type, name, tbl_name, sql)`, `application_id` and `user_version`.

Filesystem integers allow 128 bits because Windows file IDs can exceed signed
64-bit integers. The schema digest excludes root-page layout, row data, change
counters, journal mode, file hash, file size and modification times. It therefore
survives ordinary writes and WAL/checkpoint activity. A different current schema
produces MISMATCH; approving that changed schema requires reviewed re-enrollment.
This fingerprint does not attest schema history or distinguish a transient DDL
change subsequently reverted. It is not a new assigned application version or
proof of eligibility.

The incarnation witness is **not stored in the target database**. The synthetic
workspace models this independent signal through explicit administrative
`establish_incarnation` and `report_storage_replacement` actions. They are not
executive operation authorizations, and they do not write the target.

**Important limitation:** an unreported exact in-place restore can retain the same
file identity and schema. Local metadata cannot distinguish it from legitimate
SQLite writes. A test intentionally demonstrates that observation limit rather
than claiming automatic detection. The test model rejects a restore when the
independent lifecycle signal advances, including when the inode is unchanged.
Missing continuity evidence or a missing production provider yields
VERIFICATION_FAILURE. MATCH is always explicitly synthetic; it is not production
storage attestation. No production verification provider exists.

REQUIRES EXTERNAL INFRASTRUCTURE: a protected storage/maintenance authority must
retire or advance incarnation **before** any restore, replacement, relocation or
equivalent maintenance and prevent unreported changes. Durable current enrollment,
rollback-resistant administrative state, protected signing keys and host/deployment
attestation must live outside the replaceable application database.

REQUIRES IMPLEMENTATION DESIGN: how the actual deployment enforces that maintenance
boundary and provides fresh authenticated continuity to a future verifier. The
repository does not prove that storage/OS control exists. Without it, production
execution remains blocked; no amount of synthetic success clears that requirement.

## Signed immutable record and separate current state

`enrollment.py` defines `recognition-target-enrollment-v1`, with the same strict
JSON/Ed25519 envelope conventions as Slice 4, but a separate domain:
ASCII `DMV-recognition-target-enrollment-v1`, NUL, then existing canonical payload.
No signing API or private-key loader is added.

The payload contains canonical UUID enrollment ID, positive generation, registry
identity, enrolling issuer/key identities, state ENROLLED, target type
`sqlite-main-v1`, the target identity above, issuance time, administrative provenance,
and an optional predecessor reference. A reference is exactly:

`{enrollment_id, generation, record_sha256}`

The digest covers the complete canonical signed record. Initial generation is 1.
A successor uses a new UUID, generation plus one, and the exact signed predecessor
reference. A successor may identify the same path or a newly restored/relocated path.
It cannot fork from an already superseded predecessor. Historical record bytes
remain unchanged; replaying an old registration cannot reactivate it.

`SyntheticEnrollmentWorkspace` creates its own fresh temporary root and never adopts
an existing root or production file. It takes only explicit synthetic enrollment
public-key configuration, separate from executive-operation keys. Its explicit
`register` and `revoke` methods model administrative registry actions. Records are
canonical immutable strings; current/superseded/revoked state is separate. Callers
receive frozen verification facts or detached dictionaries, not capabilities.

There is no persistent registry in this slice and **no database migration**, DDL,
marker insertion or startup hook. The in-memory synthetic registry is not claimed
restart-durable or production-trusted. Production enrollment records/current status
belong in independently administered external storage, with archival retention,
authenticated availability and rollback protection. A target database row cannot
declare its own production enrollment.

## Verification

`verify_record(record_json, provider=...)` verifies historical representation,
signature and configured enrolling authority. `reference(...)` returns the exact
immutable binding. Neither establishes current enrollment or permission to mutate.

`verify_target(record_json, target_path=..., expected_reference=...,
trusted_now_utc=..., provider=...)` returns a frozen `EnrollmentResult`:

| Result | Meaning |
| --- | --- |
| MATCH | Registered, current synthetic enrollment, exact generation/digest, target and schema match |
| MISMATCH | Different binding/path/file/parent/incarnation/schema, alias, missing target or unsafe file type |
| INVALID_ENROLLMENT | Malformed/altered/unsigned/unknown/unregistered record, invalid reference or future issuance |
| REVOKED_OR_SUPERSEDED | Historically valid record is no longer current |
| VERIFICATION_FAILURE | Provider/registry/continuity unavailable, temporary SQL or filesystem failure |

Verification rejects links/reparse points and ancestor aliases, uses only targets
inside the newly allocated disposable root, and rejects paths outside it before
inspecting the target. It checks metadata before reading schema and again afterward.
Schema reads use a read-only SQLite connection/transaction, respecting committed WAL
data rather than using SQLite's `immutable=1` shortcut. SQLite may maintain normal
WAL/SHM reader bookkeeping; no target DDL or row mutation is performed. The observed
connection must have exactly one file-backed main database; attachments are refused.

Path observation before/after is not an OS-level attestation that a future writer
uses the same open file. Concurrent target replacement, storage-witness freshness,
and descriptor/commit coordination remain requirements of the future execution
boundary. This verifier neither starts that boundary nor closes its race.

## Slice 3/4 compatibility

Existing `recognition-operation-contract-v1` records retain null placeholders and
their original hashes. Nothing is backfilled or promoted.

`operations.create_operation(..., enrollment_reference=..., enrollment_provider=...,
trusted_now_utc=...)` can explicitly create `recognition-operation-contract-v2` for
a new frozen event. Its persistence approval subject additionally includes
`enrollment`. Creation requires a current synthetic MATCH; subsequent archival
retrieval does not revalidate today's registry or rewrite yesterday's record.
An existing event's operation cannot change enrollment; revision/new event/new
operation identity is required. Both formats remain synthetic and PREPARED initially.

Slice 4 now accepts the versioned enrollment reference in the existing envelope.
The exact operation/envelope digest, enrollment UUID, generation and signed-record
digest are all signed. An old authorization cannot satisfy a new generation even
when the path and other contents are unchanged. No alternate operation wrapper or
new standing authorization is introduced. Receipt matching already binds the exact
envelope enrollment field and needs no new execution behavior.

Historical/current authorization verification and target verification remain
independent facts. A cryptographically valid authorization is not proof of current
enrollment. Enrollment MATCH is not proof of signed authorization, current executive
status, dependency READY, finality or commit safety. No combined executor/admission
service is added. Existing writers accept none of these results as authority, and
production provisioning still unconditionally rejects.

## Tests and remaining boundary

Tests use independently observed filesystem values, a fixed expected schema SQL
structure, independently assembled signatures, real disposable file and parent
replacement, in-place restore with simulated external signal, schema changes,
normal writes, WAL/checkpointing, hard links, and real symlinks where permitted.
Windows symlink privilege failures skip only the real symlink case; a portable
reparse guard remains tested. A local pass does not prove hosted Linux behavior.

Slice 6 can proceed with disposable coordinator/recovery contract work. Production
admission is blocked until the independently authenticated enrollment/continuity
system, execution-boundary file identity controls, and commit/recovery protocol
are designed and provisioned. No production authority, keys or credentials are
created, and no production target or external service is contacted by this slice.

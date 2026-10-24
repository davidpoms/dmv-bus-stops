"""Installation readiness contract. Production providers and activation are absent.

READY_FOR_ACTIVATION in the disposable interface-double harness is never a
production capability. No caller-supplied provider, boolean or callback can enroll
a production installation. This models the future external boundary, not its proof.
"""

from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
import sqlite3
import tempfile
from uuid import uuid4
from weakref import WeakKeyDictionary

from . import DISABLED, RecognitionGate, activation_schema, trust
from .authorization import target_identity
from .rules import canonical, digest


DOMAIN = b"DMV-recognition-installation-ceremony-v1\x00"
FORMAT = "recognition-activation-readiness-v1"
EXTERNAL = "EXTERNAL_INFRASTRUCTURE_REQUIRED"
REPOSITORY = "REPOSITORY_VERIFIABLE"
# Exact implementation interfaces, not assertions that production services exist.
PREREQUISITES = (
    ("trust_root", EXTERNAL, "trust.configuration; protected signing-key storage"),
    ("authority_status", EXTERNAL, "status.verify_current_status"),
    ("status_continuity", EXTERNAL, "status._verified_status_transaction; protected checkpoint"),
    ("target_enrollment", EXTERNAL, "enrollment.verify_record/verify_target"),
    ("enrollment_continuity", EXTERNAL, "enrollment._observe; independent incarnation registry"),
    ("target_identity", EXTERNAL, "authorization.target_identity; host/process fencing"),
    ("dependencies", REPOSITORY, "dependencies.recheck"),
    ("policy_versions", REPOSITORY, "permanent.DEFINITIONS; execution.POLICY; operations.ENROLLED_CONTRACT"),
    ("operation_integrity", REPOSITORY, "operations.get_operation"),
    ("authorization", REPOSITORY, "trust.verify_historical_authorization/verify_authorization_time"),
    ("execution_journal", REPOSITORY, "execution_schema.check_schema; execution.execute_operation"),
    ("writer_boundary", REPOSITORY, "writer_boundary.production_guard/acquire; permanent.finalize"),
    ("recovery", REPOSITORY, "execution.reconcile_operation; SyntheticRecoveryContext"),
    ("emergency_stop", REPOSITORY, "execution.set_emergency_stop/clear_emergency_stop"),
    ("trusted_time", EXTERNAL, "explicit trusted_now_utc inputs; no production clock provider"),
    ("finality", EXTERNAL, "live_first_looks.seal_pending finality_guard; historical-only execution.POLICY"),
    ("provider_separation", REPOSITORY, "trust.configuration; registered synthetic execution contexts"),
    ("provisioning", EXTERNAL, "authority.provision_production_authority rejects"),
    ("startup", REPOSITORY, "RecognitionGate/DISABLED; API issuance=False"),
    ("database_selection", REPOSITORY, "src.api.deployment.configured_database; no fallback"),
    ("explorer_isolation", REPOSITORY, "execution dispatches permanent.finalize only; separate Explorer schema"),
    ("schema_versions", REPOSITORY, "event/operation/permanent/execution_schema.check_schema"),
    ("administrative_identity", EXTERNAL, "authenticated executive identity and TOTP; no production provider"),
    ("activation_storage", EXTERNAL, "protected installation ledger, continuity and process fencing"),
    ("deployment_controls", EXTERNAL, "backup/restore policy and reviewed deployment controls"),
)
KEYS = frozenset(row[0] for row in PREREQUISITES)
REQUIRED_STATES = dict(zip((row[0] for row in PREREQUISITES), (
    "CONFIGURED", "CURRENT", "PROTECTED", "MATCH", "PROTECTED", "MATCH", "READY",
    "SUPPORTED", "VALID", "VALID", "AVAILABLE", "ENFORCED", "AVAILABLE", "AVAILABLE",
    "TRUSTED", "HISTORICAL_ONLY", "ENFORCED", "PROVISIONED", "FAIL_CLOSED",
    "EXPLICIT_NO_FALLBACK", "ISOLATED", "COMPATIBLE", "AUTHENTICATED_WITH_MFA",
    "PROTECTED", "VERIFIED")))
STATES = frozenset(("NOT_ACTIVATED", "ACTIVATED", "SUSPENDED", "DEACTIVATED", "UNKNOWN_RECOVERY_REQUIRED"))
OUTCOMES = frozenset(("SATISFIED", "BLOCKED", "EXTERNAL_PREREQUISITE_UNVERIFIED",
                      "CONFIGURATION_ERROR", "INTEGRITY_FAILURE"))
_workspaces = WeakKeyDictionary()
_assessments = WeakKeyDictionary()


@dataclass(frozen=True)
class InterfaceEvidence:
    """Approved interface double's observation, accepted only in a fresh test root.

    SATISFIED is a fixture assertion, never proof about an actual installation.
    Reference is a non-secret evidence digest, not arbitrary text or credentials.
    """
    prerequisite: str
    outcome: str
    observed_state: str
    observed_at_utc: str
    expires_at_utc: str
    evidence_sha256: str


@dataclass(frozen=True)
class Check:
    prerequisite: str
    boundary: str
    outcome: str
    reason: str
    interface: str
    evidence_sha256: str | None = None
    observed_state: str | None = None


@dataclass(frozen=True, eq=False)
class ReadinessAssessment:
    canonical_json: str
    sha256: str

    @property
    def status(self):
        return trust.load(self.canonical_json)["status"]

    @property
    def production_ready(self):
        # No production provider is provisioned in this repository.
        return False


@dataclass(frozen=True)
class ActivationState:
    state: str
    sequence: int
    history_sha256: str | None
    scope: str
    production_admitted: bool = False


@dataclass(frozen=True)
class ActivationResult:
    result: str
    state: ActivationState
    reason: str


class SyntheticActivationWorkspace:
    """Fresh isolated interface-double harness; cannot adopt any existing store.

    Public keys only. The designated actor is a synthetic administrative identity,
    not a claim that an ordinary Slice 4 issuance grant authorizes administration.
    """

    def __init__(self, *, provider, administrative_authority_id):
        trust.require(type(provider) is trust.SyntheticTrustProvider, "synthetic_provider_required")
        config = trust.configuration(provider)
        key = next((k for k in config["authority_keys"] if k["authority_id"] == administrative_authority_id), None)
        trust.require(key is not None, "synthetic_administrative_identity_missing")
        temporary = tempfile.TemporaryDirectory(prefix="recognition-activation-disposable-")
        root = Path(temporary.name).resolve()
        self.directory = root
        _workspaces[self] = dict(temporary=temporary, root=root, identity=None, provider=provider, key=canonical(key),
            installation_id=str(uuid4()), configuration_sha256=digest(config))

    def install(self):
        """Explicit disposable creation; never performed by assess/startup/state."""
        data = _workspace(self, installed=False)
        path = data["root"] / "ledger.sqlite"
        with path.open("xb"):
            pass
        data["identity"] = target_identity(path)
        with _store(self) as conn:
            conn.execute("BEGIN IMMEDIATE")
            activation_schema.install(conn)
            body = dict(installation_id=data["installation_id"], scope="DISPOSABLE_INTERFACE_DOUBLES",
                        configuration_sha256=data["configuration_sha256"])
            conn.execute("INSERT INTO recognition_activation_installation VALUES(1,?,?)", (canonical(body), digest(body)))
            conn.commit()

    def cleanup(self):
        data = _workspaces.pop(self, None)
        if data:
            data["temporary"].cleanup()


def _workspace(workspace, *, installed=True):
    trust.require(type(workspace) is SyntheticActivationWorkspace and workspace in _workspaces,
                  "production_activation_provider_unavailable")
    data = _workspaces[workspace]
    trust.require(workspace.directory == data["root"] and data["root"].is_dir(), "disposable_root_unavailable")
    if installed:
        trust.require(data["identity"] is not None and target_identity(data["root"] / "ledger.sqlite") == data["identity"],
                      "activation_storage_identity_mismatch")
    return data


@contextmanager
def _store(workspace):
    data = _workspace(workspace)
    conn = sqlite3.connect((data["root"] / "ledger.sqlite").as_uri() + "?mode=rw", uri=True)
    try:
        conn.execute("PRAGMA synchronous=FULL")
        yield conn
    finally:
        if conn.in_transaction:
            conn.rollback()
        conn.close()


def _ledger(conn, data):
    activation_schema.check_schema(conn)
    rows = conn.execute("SELECT body_json,body_sha256 FROM recognition_activation_installation").fetchall()
    expected = dict(installation_id=data["installation_id"], scope="DISPOSABLE_INTERFACE_DOUBLES",
                    configuration_sha256=data["configuration_sha256"])
    trust.require(rows == [(canonical(expected), digest(expected))], "activation_installation_mismatch")
    previous, state, seq, last_time = None, "NOT_ACTIVATED", 0, None
    for sequence, ceremony_id, serialized, sha in conn.execute(
            "SELECT sequence,ceremony_id,body_json,body_sha256 FROM recognition_activation_history ORDER BY sequence"):
        row = trust.load(serialized)
        trust.require(digest(row) == sha and row["previous_sha256"] == previous and sequence == seq + 1
                      and row["prior_state"] == state and row["sequence"] == sequence
                      and row["installation_id"] == data["installation_id"], "activation_history_integrity_failure")
        _verify_ceremony(row["ceremony"], data, row["timestamp_utc"])
        p = row["ceremony"]["payload"]
        trust.require(p["ceremony_id"] == ceremony_id and p["expected_sequence"] == seq
                      and p["readiness_sha256"] == digest(row["readiness"])
                      and p["prior_history_sha256"] == previous and p["prior_state"] == state
                      and p["generations"] == row["readiness"]["generations"]
                      and row["action"] == p["action"] and row["actor"] == p["authority_id"]
                      and row["new_state"] == _transition(state, p["action"]), "activation_history_binding_failure")
        trust.require(last_time is None or trust.utc(last_time) <= trust.utc(row["timestamp_utc"]), "activation_clock_rollback")
        state, seq, previous, last_time = row["new_state"], sequence, sha, row["timestamp_utc"]
    return ActivationState(state, seq, previous, "DISPOSABLE_INTERFACE_DOUBLES"), last_time


def get_activation_state(installation=None):
    if installation is None:
        return ActivationState("NOT_ACTIVATED", 0, None, "PRODUCTION_UNPROVISIONED")
    data = _workspace(installation)
    with _store(installation) as conn:
        return _ledger(conn, data)[0]


def _repository_checks():
    from . import dependencies, execution, execution_schema, operations, permanent, writer_boundary
    from src.api.deployment import configured_database
    return {
        "dependencies": callable(dependencies.recheck),
        "policy_versions": operations.ENROLLED_CONTRACT == "recognition-operation-contract-v2"
            and execution.POLICY == {"reference": "atomic-historical-v1", "quarantine_categories": [], "other_categories": []},
        "operation_integrity": callable(operations.get_operation),
        "authorization": callable(trust.verify_historical_authorization) and callable(trust.verify_authorization_time),
        "execution_journal": callable(execution_schema.check_schema) and callable(execution.execute_operation),
        "writer_boundary": callable(writer_boundary.production_guard) and callable(writer_boundary.acquire) and callable(permanent.finalize),
        "recovery": callable(execution.reconcile_operation),
        "emergency_stop": callable(execution.set_emergency_stop) and callable(execution.clear_emergency_stop),
        "provider_separation": callable(trust.configuration),
        "startup": DISABLED == RecognitionGate(capture=False, issuance=False),
        "database_selection": configured_database({}) is None and configured_database({"DMV_BUS_STOPS_DB": "relative.sqlite"}) is None,
        "explorer_isolation": callable(permanent.finalize),
        "schema_versions": callable(execution_schema.check_schema),
    }


def assess_production_readiness(*, installation=None, evidence=(), generations=None, trusted_now_utc=None):
    """Read-only, structured fail-closed report. No target/remote access or activation.

    Evidence is accepted only for the registered disposable interface-double scope.
    Production has no approved loader; supplied facts/providers cannot change that.
    """
    test_scope = type(installation) is SyntheticActivationWorkspace and installation in _workspaces
    checks, state = [], ActivationState("NOT_ACTIVATED", 0, None,
        "DISPOSABLE_INTERFACE_DOUBLES" if test_scope else "PRODUCTION_UNPROVISIONED")
    observations = {}
    malformed = False
    if test_scope:
        try:
            state = get_activation_state(installation)
            trust.utc(trusted_now_utc)
            trust.fields(generations, {"trust", "status", "enrollment", "deployment"})
            for value in generations.values():
                trust.integer(value, 1)
            trust.require(type(evidence) in (tuple, list), "invalid_evidence")
            for item in evidence:
                trust.require(type(item) is InterfaceEvidence and item.prerequisite in KEYS
                              and item.prerequisite not in observations and item.outcome in OUTCOMES, "invalid_evidence")
                trust.sha(item.evidence_sha256)
                trust.require(type(item.observed_state) is str and item.observed_state.replace("_", "").isalnum()
                              and item.observed_state.isupper() and len(item.observed_state) <= 64, "invalid_interface_state")
                trust.require(trust.utc(item.observed_at_utc) < trust.utc(item.expires_at_utc), "invalid_evidence_interval")
                observations[item.prerequisite] = item
        except (trust.TrustError, OSError, sqlite3.Error, TypeError):
            malformed = True
    try:
        repository = _repository_checks()
    except Exception:
        repository = {}  # Unverifiable repository interfaces cannot become readiness.
    for key, boundary, interface in PREREQUISITES:
        item = observations.get(key)
        if boundary == REPOSITORY and not repository.get(key, False):
            outcome, reason = "INTEGRITY_FAILURE", "repository_contract_unavailable"
        elif malformed:
            outcome, reason = "INTEGRITY_FAILURE", "invalid_disposable_assessment_context"
        elif not test_scope:
            outcome, reason = "EXTERNAL_PREREQUISITE_UNVERIFIED", "production_runtime_evidence_unavailable"
        elif item is None:
            outcome, reason = "EXTERNAL_PREREQUISITE_UNVERIFIED", "required_evidence_missing"
        elif not (trust.utc(item.observed_at_utc) <= trust.utc(trusted_now_utc) < trust.utc(item.expires_at_utc)):
            outcome, reason = "BLOCKED", "evidence_expired_or_not_yet_valid"
        elif item.outcome == "SATISFIED" and item.observed_state != REQUIRED_STATES[key]:
            outcome, reason = "BLOCKED", "unsafe_interface_state"
        else:
            outcome, reason = item.outcome, "interface_double_verified" if item.outcome == "SATISFIED" else "prerequisite_rejected"
        checks.append(Check(key, boundary, outcome, reason, interface, item.evidence_sha256 if item else None,
                            item.observed_state if item else None))
    ready = all(c.outcome == "SATISFIED" for c in checks)
    body = dict(format=FORMAT, status="READY_FOR_ACTIVATION" if ready else "BLOCKED",
                scope=state.scope, installation_id=_workspaces[installation]["installation_id"] if test_scope else None,
                production_ready=False, assessed_at_utc=trusted_now_utc if test_scope and not malformed else None,
                generations=generations if test_scope and not malformed else None,
                activation_state=asdict(state), checks=[asdict(c) for c in checks])
    result = ReadinessAssessment(canonical(body), digest(body))
    if test_scope and not malformed:
        _assessments[result] = (installation, tuple(evidence), canonical(generations))
    return result


def _transition(state, action):
    allowed = {"activate": ({"NOT_ACTIVATED", "DEACTIVATED", "SUSPENDED"}, "ACTIVATED"),
               "deactivate": ({"ACTIVATED", "SUSPENDED"}, "DEACTIVATED"),
               "suspend": ({"ACTIVATED"}, "SUSPENDED")}
    trust.require(action in allowed and state in allowed[action][0], "invalid_activation_transition")
    return allowed[action][1]


def ceremony_payload(installation, assessment, *, action, ceremony_id, issued_at_utc, expires_at_utc):
    """Non-secret signing contract; no signer, authentication or authority minted."""
    data = _workspace(installation)
    trust.require(assessment in _assessments and _assessments[assessment][0] is installation, "registered_assessment_required")
    state = get_activation_state(installation)
    key = trust.load(data["key"])
    return dict(format="recognition-activation-ceremony-v1", installation_id=data["installation_id"],
                authority_id=key["authority_id"], key_id=key["key_id"], action=action, ceremony_id=ceremony_id,
                expected_sequence=state.sequence, prior_state=state.state, prior_history_sha256=state.history_sha256,
                readiness_sha256=assessment.sha256, generations=trust.load(assessment.canonical_json)["generations"],
                issued_at_utc=issued_at_utc, expires_at_utc=expires_at_utc)


def _verify_ceremony(ceremony, data, now):
    trust.fields(ceremony, {"payload", "signature"})
    p = ceremony["payload"]
    trust.fields(p, {"format", "installation_id", "authority_id", "key_id", "action", "ceremony_id", "expected_sequence",
                     "prior_state", "prior_history_sha256", "readiness_sha256", "generations", "issued_at_utc", "expires_at_utc"})
    key = trust.load(data["key"])
    trust.require(p["format"] == "recognition-activation-ceremony-v1" and p["installation_id"] == data["installation_id"]
                  and (p["authority_id"], p["key_id"]) == (key["authority_id"], key["key_id"]), "administrative_identity_mismatch")
    trust.identity(p["ceremony_id"])
    trust.integer(p["expected_sequence"])
    trust.sha(p["readiness_sha256"])
    verify_at = p["issued_at_utc"] if now is None else now
    trust.require(trust.utc(p["issued_at_utc"]) <= trust.utc(verify_at) < trust.utc(p["expires_at_utc"]), "ceremony_not_current")
    trust.verify_signature(key["public_key"], ceremony["signature"], DOMAIN + canonical(p).encode())


def _change(installation, assessment, ceremony_json, now, action):
    if type(installation) is not SyntheticActivationWorkspace or installation not in _workspaces:
        return ActivationResult("BLOCKED", get_activation_state(), "production_activation_provider_unavailable")
    try:
        data = _workspace(installation)
        trust.utc(now)
        trust.require(type(assessment) is ReadinessAssessment and assessment in _assessments
                      and _assessments[assessment][0] is installation, "registered_assessment_required")
        report = trust.load(assessment.canonical_json)
        trust.require(digest(report) == assessment.sha256, "assessment_integrity_failure")
        ceremony = trust.load(ceremony_json)
        _verify_ceremony(ceremony, data, None)
        p = ceremony["payload"]
        trust.require(p["action"] == action and p["readiness_sha256"] == assessment.sha256
                      and p["generations"] == report["generations"], "ceremony_assessment_mismatch")
        with _store(installation) as conn:
            conn.execute("BEGIN IMMEDIATE")
            state, last_time = _ledger(conn, data)
            prior = conn.execute("SELECT body_json FROM recognition_activation_history WHERE ceremony_id=?", (p["ceremony_id"],)).fetchone()
            if prior:
                trust.require(trust.load(prior[0])["ceremony"] == ceremony, "ceremony_identity_conflict")
                return ActivationResult("ALREADY_" + {"activate": "ACTIVATED", "deactivate": "DEACTIVATED", "suspend": "SUSPENDED"}[action],
                                        state, "ceremony_previously_applied")
            _verify_ceremony(ceremony, data, now)
            trust.require(last_time is None or trust.utc(last_time) <= trust.utc(now), "activation_clock_rollback")
            trust.require(p["expected_sequence"] == state.sequence and p["prior_state"] == state.state
                          and p["prior_history_sha256"] == state.history_sha256
                          and report["activation_state"] == asdict(state), "stale_activation_ceremony")
            if action == "activate":
                trust.require(assessment.status == "READY_FOR_ACTIVATION", "readiness_required")
                _, evidence, generations = _assessments[assessment]
                fresh = assess_production_readiness(installation=installation, evidence=evidence,
                    generations=trust.load(generations), trusted_now_utc=now)
                trust.require(fresh.status == "READY_FOR_ACTIVATION", "readiness_no_longer_current")
                if state.state == "ACTIVATED":
                    return ActivationResult("ALREADY_ACTIVATED", state, "installation_already_activated")
            new_state = _transition(state.state, action)
            row = dict(installation_id=data["installation_id"], sequence=state.sequence + 1,
                       action=action, actor=p["authority_id"], prior_state=state.state, new_state=new_state,
                       timestamp_utc=now, previous_sha256=state.history_sha256, readiness=report, ceremony=ceremony)
            sha = digest(row)
            conn.execute("INSERT INTO recognition_activation_history VALUES(?,?,?,?)",
                         (state.sequence + 1, p["ceremony_id"], canonical(row), sha))
            conn.commit()
            return ActivationResult(new_state, ActivationState(new_state, state.sequence + 1, sha, state.scope), "disposable_ceremony_applied")
    except (trust.TrustError, OSError, sqlite3.Error, TypeError, KeyError):
        # A failed/uncertain store never admits production; caller inspects ledger.
        return ActivationResult("BLOCKED", ActivationState("UNKNOWN_RECOVERY_REQUIRED", 0, None, "UNVERIFIED"), "activation_ceremony_or_storage_unverified")


def activate_production(installation=None, *, assessment=None, ceremony_json=None, trusted_now_utc=None):
    return _change(installation, assessment, ceremony_json, trusted_now_utc, "activate")


def deactivate_production(installation=None, *, assessment=None, ceremony_json=None, trusted_now_utc=None):
    return _change(installation, assessment, ceremony_json, trusted_now_utc, "deactivate")


def suspend_production(installation=None, *, assessment=None, ceremony_json=None, trusted_now_utc=None):
    return _change(installation, assessment, ceremony_json, trusted_now_utc, "suspend")

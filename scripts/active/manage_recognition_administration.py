"""Explicit trusted-operator setup/rebind/MFA recovery. Never runs recognition."""

import argparse
from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.review.recognition import administration as a
from src.review.recognition.rules import canonical, digest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("preview", "inspect-filesystem-rebind", "install", "install-approvals", "install-readiness", "readiness", "install-contracts", "create-operation", "inspect-operation", "scan-approved", "advance-restore", "rebind-filesystem-identity", "migrate-runtime-profile-contract", "migrate-runtime-execution-attempt-storage", "migrate-runtime-enrollment-transition-storage", "issue-runtime-challenge", "enroll-runtime-profile", "enroll-transition-runtime-profile", "reset-mfa"))
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--key-file", type=Path, help="existing host-held Fernet key file; never generated here; not needed for inspect-filesystem-rebind")
    parser.add_argument("--operator")
    parser.add_argument("--reason")
    parser.add_argument("--installation-id")
    parser.add_argument("--owner-id", type=int)
    parser.add_argument("--expected-generation", type=int)
    parser.add_argument("--target-id")
    parser.add_argument("--source-binding-sha256")
    parser.add_argument("--confirm-issue-runtime-challenge", action="store_true",
                        help="confirm local challenge issuance only; stdout contains a one-time nonce")
    parser.add_argument('--challenge-id')
    parser.add_argument('--challenge-sha256')
    parser.add_argument('--evidence-file', type=Path)
    parser.add_argument('--approved-review-sha256')
    parser.add_argument('--approved-observation-sha256')
    parser.add_argument('--confirm-private-log-review', action='store_true')
    parser.add_argument('--confirm-enroll-runtime-profile', action='store_true')
    parser.add_argument('--plan-id')
    parser.add_argument('--plan-sha256')
    parser.add_argument("--target-sha256")
    parser.add_argument("--create-control", action="store_true")
    parser.add_argument("--confirm-mfa-reset", action="store_true")
    parser.add_argument("--request-file", type=Path)
    parser.add_argument("--operation-id")
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args(argv)
    if args.action == 'inspect-filesystem-rebind':
        if args.expected_generation is None:
            parser.error('--expected-generation is required for inspect-filesystem-rebind')
        from src.review.recognition.filesystem_rebind_inspection import inspect_rebind
        print(canonical(inspect_rebind(args.target, args.control, expected_generation=args.expected_generation)))
        return
    if args.key_file is None:
        parser.error('--key-file is required for this action')
    config = a.LocalAdministration(args.target, args.control, args.key_file)
    config.paths()
    if args.action == "preview":
        with a.connect(config.target) as conn:
            observation = a.observe_target(conn)
        print(canonical(dict(target=observation, target_sha256=digest(observation))))
        return
    if not args.operator or not args.reason:
        parser.error("--operator and --reason are required for an administrative ceremony")
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    if args.action in ('enroll-runtime-profile','enroll-transition-runtime-profile'):
        required = (args.installation_id,args.target_id,args.source_binding_sha256,args.challenge_id,
                    args.challenge_sha256,args.evidence_file,args.approved_review_sha256,args.approved_observation_sha256)
        if (not all(required) or args.expected_generation is None or args.owner_id is None
                or not args.confirm_private_log_review or not args.confirm_enroll_runtime_profile):
            parser.error('enrollment requires explicit scope, expected generation, evidence file, approved digests, '
                         '--confirm-private-log-review and --confirm-enroll-runtime-profile')
        from src.review.recognition import runtime_enrollment as enrollment
        enroll = enrollment.enroll_runtime_profile
        transition_scope = {}
        if args.action == 'enroll-transition-runtime-profile':
            if not args.plan_id or not args.plan_sha256:
                parser.error('transition enrollment requires --plan-id and --plan-sha256')
            from src.review.recognition.runtime_enrollment_transition import enroll_transition_runtime_profile
            enroll = enroll_transition_runtime_profile
            transition_scope = dict(plan_id=args.plan_id,plan_sha256=args.plan_sha256)
        import getpass
        import os
        import warnings
        try:
            a.need(args.evidence_file.is_absolute(), 'explicit_evidence_path_required')
            for protected in (config.target,config.control,config.key_file):
                a.need(args.evidence_file.resolve() != protected.resolve()
                       and (not protected.exists() or not args.evidence_file.samefile(protected)), 'separate_evidence_file_required')
            with args.evidence_file.open('rb') as source:
                opened = os.fstat(source.fileno())
                for protected in (config.target,config.control,config.key_file):
                    if protected.exists():
                        observed = protected.stat()
                        a.need((opened.st_dev,opened.st_ino) != (observed.st_dev,observed.st_ino),
                               'separate_evidence_file_required')
                raw = source.read(enrollment.MAX_REVIEW_BYTES + 1)
            a.need(len(raw) <= enrollment.MAX_REVIEW_BYTES, 'runtime_review_too_large')
            serialized = raw.decode('utf-8')
            enrollment.parse_review(serialized)
            with warnings.catch_warnings():
                warnings.simplefilter('error', getpass.GetPassWarning)
                nonce = getpass.getpass('Challenge nonce (hidden; never stored): ')
            result = enroll(config,serialized,nonce,**transition_scope,
                expected_generation=args.expected_generation,installation_id=args.installation_id,
                target_id=args.target_id,owner_id=args.owner_id,source_binding_sha256=args.source_binding_sha256,
                challenge_id=args.challenge_id,challenge_sha256=args.challenge_sha256,
                approved_review_sha256=args.approved_review_sha256,approved_observation_sha256=args.approved_observation_sha256,
                operator=args.operator,reason=args.reason,confirm_private_log_review=args.confirm_private_log_review,
                confirm_enroll_runtime_profile=args.confirm_enroll_runtime_profile)
        except Exception:
            parser.exit(1, 'Runtime enrollment failed; inspect trusted state before retrying. No runtime authority enabled.\n')
        print(canonical(result))
        return
    if args.action == 'issue-runtime-challenge':
        if (args.expected_generation is None or not args.installation_id or not args.target_id
                or args.owner_id is None or not args.source_binding_sha256
                or not args.confirm_issue_runtime_challenge):
            parser.error('--expected-generation, --installation-id, --target-id, --owner-id, '
                         '--source-binding-sha256 and --confirm-issue-runtime-challenge are required; '
                         'stdout returns the nonce once: do not redirect it to persistent logs')
        from src.review.recognition.runtime_challenges import issue_challenge
        print(canonical(issue_challenge(config, expected_generation=args.expected_generation,
            installation_id=args.installation_id, target_id=args.target_id, owner_id=args.owner_id,
            source_binding_sha256=args.source_binding_sha256, operator=args.operator,
            reason=args.reason, now=now)))
        return
    if args.action == 'migrate-runtime-enrollment-transition-storage':
        if args.expected_generation is None:
            parser.error('--expected-generation is required')
        from src.review.recognition import runtime_enrollment_transition_schema
        print(canonical(runtime_enrollment_transition_schema.migrate(config,
            expected_generation=args.expected_generation, operator=args.operator, reason=args.reason)))
        return
    if args.action == 'migrate-runtime-execution-attempt-storage':
        if args.expected_generation is None:
            parser.error('--expected-generation is required')
        from src.review.recognition import runtime_execution_attempt_schema
        print(canonical(runtime_execution_attempt_schema.migrate(config,
            expected_generation=args.expected_generation, operator=args.operator, reason=args.reason)))
        return
    if args.action == 'migrate-runtime-profile-contract':
        if args.expected_generation is None:
            parser.error('--expected-generation is required')
        generation = a.migrate_runtime_profile_contract(config, expected_generation=args.expected_generation,
            operator=args.operator, reason=args.reason, now=now)
        print(canonical(dict(generation=generation, production_state='NOT_ACTIVATED', runtime_access='BLOCKED')))
        return
    if args.action == "install-readiness":
        from src.review.recognition import local_readiness
        local_readiness.install(config, operator=args.operator, reason=args.reason, now=now)
        print("Local readiness installed NOT_ACTIVATED; production remains blocked.")
        return
    if args.action in ("install-contracts", "create-operation", "inspect-operation", "scan-approved", "readiness"):
        from src.review.recognition import production_operations as operations, admin_auth
        if args.action == "install-contracts":
            a.get_installation_control(config)  # Pin the intended existing installation before DDL.
            with a.connect(config.target, write=True) as conn:
                conn.execute("BEGIN IMMEDIATE")
                operations.install_target(conn)
                conn.commit()
            print("Contract schema installed. If the pinned schema changed, explicit preview/advance-restore is required; production remains blocked.")
            return
        if args.action == "scan-approved":
            print(canonical(operations.continue_pending(config, now=now, limit=args.limit)))
            return
        import getpass
        token = getpass.getpass("Administrative session token (not echoed): ")
        admin_auth.require_recognition_admin(config, token, now=now)
        if args.action == "readiness":
            from src.review.recognition import local_readiness
            print(canonical(local_readiness.assess(config, now=now)))
            return
        if args.action == "create-operation":
            if not args.request_file:
                parser.error("--request-file is required")
            import json
            print(canonical(operations.create_operation(config, token, json.loads(args.request_file.read_text(encoding="utf-8")), now=now)))
        else:
            if not args.operation_id:
                parser.error("--operation-id is required")
            print(canonical(operations.inspect_operation(config, args.operation_id)))
        return
    if args.action == "install":
        if not args.installation_id or not args.owner_id:
            parser.error("--installation-id and --owner-id are required")
        if args.create_control:
            with config.control.open("xb"):
                pass
            config.control.chmod(0o600)
        a.install(config, installation_id=args.installation_id, owner_id=args.owner_id,
                  operator=args.operator, reason=args.reason, now=now)
    elif args.action == "install-approvals":
        from src.review.recognition import approvals
        approvals.install(config, operator=args.operator, reason=args.reason, now=now)
    elif args.action in ("advance-restore", "rebind-filesystem-identity"):
        if args.expected_generation is None or not args.target_sha256:
            parser.error("--expected-generation and --target-sha256 from preview are required")
        ceremony = a.rebind_filesystem_identity if args.action == "rebind-filesystem-identity" else a.advance_restore_generation
        ceremony(config, expected_generation=args.expected_generation,
            expected_target_sha256=args.target_sha256, operator=args.operator, reason=args.reason, now=now)
    else:
        if args.expected_generation is None or not args.confirm_mfa_reset:
            parser.error("--expected-generation and --confirm-mfa-reset are required")
        a.reset_mfa(config, expected_generation=args.expected_generation, operator=args.operator, reason=args.reason, now=now)
    print("Local administrative control updated; production recognition remains blocked.")


if __name__ == "__main__":
    main()

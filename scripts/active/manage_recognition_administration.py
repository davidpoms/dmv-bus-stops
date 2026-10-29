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
    parser.add_argument("action", choices=("preview", "install", "install-approvals", "install-readiness", "readiness", "install-contracts", "create-operation", "inspect-operation", "scan-approved", "advance-restore", "rebind-filesystem-identity", "migrate-runtime-profile-contract", "issue-runtime-challenge", "reset-mfa"))
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--key-file", type=Path, required=True, help="existing host-held Fernet key file; never generated here")
    parser.add_argument("--operator")
    parser.add_argument("--reason")
    parser.add_argument("--installation-id")
    parser.add_argument("--owner-id", type=int)
    parser.add_argument("--expected-generation", type=int)
    parser.add_argument("--target-id")
    parser.add_argument("--source-binding-sha256")
    parser.add_argument("--confirm-issue-runtime-challenge", action="store_true",
                        help="confirm local challenge issuance only; stdout contains a one-time nonce")
    parser.add_argument("--target-sha256")
    parser.add_argument("--create-control", action="store_true")
    parser.add_argument("--confirm-mfa-reset", action="store_true")
    parser.add_argument("--request-file", type=Path)
    parser.add_argument("--operation-id")
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args(argv)
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

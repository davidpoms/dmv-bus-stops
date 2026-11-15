"""Explicit trusted-owner device-drift recovery, claim-schema migration only."""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.api.sqlite_runtime import load_production_sqlite

load_production_sqlite()  # Must precede any sqlite3-dependent project imports.

from src.review.recognition import administration as a
from src.review.recognition import deployment_claim_recovery as recovery
from src.review.recognition import runtime_execution_claim_schema as claims
from src.review.recognition.rules import canonical


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('preview', 'authorize', 'migrate', 'status'))
    parser.add_argument('--target', type=Path, required=True)
    parser.add_argument('--control', type=Path, required=True)
    parser.add_argument('--key-file', type=Path, required=True)
    parser.add_argument('--installation-id', required=True)
    parser.add_argument('--target-id', required=True)
    parser.add_argument('--expected-generation', type=int, required=True)
    parser.add_argument('--owner-id', type=int, required=True)
    parser.add_argument('--operation', required=True, choices=(claims.ACTION,))
    parser.add_argument('--operator')
    parser.add_argument('--reason')
    parser.add_argument('--approved-snapshot-sha256')
    parser.add_argument('--recovery-sha256')
    parser.add_argument('--accept-storage-continuity-uncertainty', action='store_true')
    args = parser.parse_args(argv)
    config = a.LocalAdministration(args.target, args.control, args.key_file)
    # Scope checks before any mutation; core APIs repeat scope under reservations.
    from src.review.recognition.runtime_challenges import _deployment_binding
    with a.connect(config.control) as control:
        binding = _deployment_binding(control)
        a.need(args.expected_generation == binding['generation'] == 5
               and args.installation_id == binding['installation_id']
               and args.target_id == binding['target_id'] and args.owner_id == binding['owner_id'],
               'claim_recovery_cli_scope_mismatch')
    if args.action == 'preview':
        print(canonical(recovery.preview(config)))
        return
    if args.action == 'status':
        if not args.recovery_sha256:
            parser.error('--recovery-sha256 is required')
        print(canonical(recovery.inspect(config, args.recovery_sha256)))
        return
    if not args.operator or not args.reason:
        parser.error('--operator and --reason are required')
    if args.action == 'authorize':
        if not args.approved_snapshot_sha256 or not args.accept_storage_continuity_uncertainty:
            parser.error('explicit snapshot digest and --accept-storage-continuity-uncertainty are required')
        print(recovery.BOUNDARY)
        confirmation = input('Type the reviewed snapshot SHA256 to approve its old/new identities and exact scope: ')
        a.need(confirmation == args.approved_snapshot_sha256, 'claim_recovery_confirmation_mismatch')
        result = recovery.authorize(config, approved_snapshot_sha256=confirmation, owner_id=args.owner_id,
                                    operator=args.operator, reason=args.reason)
    else:
        if not args.recovery_sha256:
            parser.error('--recovery-sha256 is required')
        result = claims.migrate(config, expected_generation=args.expected_generation,
                                operator=args.operator, reason=args.reason, recovery_sha256=args.recovery_sha256)
    print(canonical(result))


if __name__ == '__main__':
    main()

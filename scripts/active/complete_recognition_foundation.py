"""Signed-owner generation-5 foundation maintenance. Never activates recognition."""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
from src.api.sqlite_runtime import load_production_sqlite

load_production_sqlite()  # Must run before any sqlite3-dependent project import.

from src.review.recognition import administration as a
from src.review.recognition import runtime_target_schema_completion as completion
from src.review.recognition.rules import canonical
from src.review.recognition.trust import fields, load, require


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        # argparse's normal message can echo an unrecognized credential argument.
        self.exit(2,'Invalid foundation maintenance arguments; use --help.\n')


def main(argv=None):
    parser = _Parser(description=__doc__)
    parser.add_argument('action',choices=('preview','complete'))
    parser.add_argument('--target',type=Path,required=True)
    parser.add_argument('--control',type=Path,required=True)
    parser.add_argument('--key-file',type=Path,required=True)
    parser.add_argument('--expected-generation',type=int,choices=(5,6),required=True)
    parser.add_argument('--authorization',type=Path,required=True,
                        help='Existing independently signed JSON envelope; never a raw session token')
    parser.add_argument('--approved-plan-sha256')
    args = parser.parse_args(argv)
    if args.action == 'complete' and not args.approved_plan_sha256:
        parser.error('--approved-plan-sha256 is required for complete')
    if args.action == 'preview' and args.approved_plan_sha256 is not None:
        parser.error('--approved-plan-sha256 applies only to complete')
    try:
        config = a.LocalAdministration(args.target,args.control,args.key_file)
        config.paths()
        path = args.authorization
        require(path.is_absolute() and path.is_file() and not path.is_symlink()
                and path.stat().st_nlink == 1 and path.stat().st_size <= 131072,
                'foundation_authorization_file_required')
        # An envelope contains only the existing canonical signed body and signature.
        # Never print it or any exception text/args on failure.
        with path.open('r',encoding='utf-8') as handle:
            encoded = handle.read(131073)
        require(len(encoded.encode('utf-8')) <= 131072,'foundation_authorization_file_required')
        artifact = load(encoded)
        fields(artifact,('serialized_approval','signature'))
        if args.action == 'preview':
            result = completion.preview_approved(config,**artifact)
        else:
            # This is only an operator-expectation preflight. The backend still
            # verifies the signature, plan, current scope and final generation.
            approval = load(artifact['serialized_approval'])
            fields(approval['subject'], ('kind','plan'))
            require(approval['subject']['kind'] == completion.lineage.KIND,
                    'foundation_approval_purpose')
            generation = approval['subject']['plan']['generation']
            require(type(generation) is int and generation == args.expected_generation,
                    'foundation_cli_generation_mismatch')
            # Digest confirmation is explicit; signing remains independent of this tool.
            confirmation = input('Type the approved preview plan SHA256 to install only its event foundation: ')
            require(confirmation == args.approved_plan_sha256,'foundation_plan_confirmation_mismatch')
            result = completion.complete_approved(config,approved_plan_sha256=confirmation,**artifact)
        require(result['generation'] == args.expected_generation,'foundation_cli_generation_mismatch')
        print(canonical(result))
        return 0
    except Exception:
        print(canonical(dict(error='foundation_completion_outcome_unconfirmed' if args.action == 'complete'
                             else 'foundation_preview_rejected',execution_authority=False,
                             inspect_before_retry=args.action == 'complete')),file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

"""Explicit offline recovery + local custodian operations. No HTTP or activation."""
import argparse
import base64
import getpass
from pathlib import Path
import sys
import warnings

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.operator import recognition_governance as operator


def _read(path):
    operator._protected(path)
    operator.require(path.stat().st_size <= 262144)
    raw = path.read_text(encoding='utf-8')
    import json
    value = json.loads(raw, object_pairs_hook=operator._object,
                       parse_constant=lambda _: operator.require(False))
    operator.require(raw == operator.canonical(value))
    return value


def _secret(prompt):
    if operator.os.name == 'nt' and not operator._windows_console_available():
        raise operator.SecureTerminalRequired()
    with warnings.catch_warnings():
        warnings.simplefilter('error', getpass.GetPassWarning)
        return getpass.getpass(prompt)


def keygen(private_key, public_key, installation_id, owner_id):
    """Recovery-only Ed25519 key; normal governance sign() cannot consume it."""
    private_key = operator._outside_repository(private_key)
    public_key = operator._path(public_key)
    operator.require(private_key != public_key and not private_key.exists() and not public_key.exists())
    operator._protected(private_key.parent, private=True)
    operator._protected(public_key.parent)
    password = operator._password(confirm=True)
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, PublicFormat, BestAvailableEncryption
    from src.review.recognition.runtime_governance_recovery import KEY_FORMAT, validate_key
    key = Ed25519PrivateKey.generate()
    public = key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    value = dict(format=KEY_FORMAT, installation_id=installation_id, owner_id=owner_id,
                 public_key=base64.b64encode(public).decode())
    validate_key(value)
    operator._publish(private_key, key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8,
                                                    BestAvailableEncryption(password)), private=True)
    operator._publish(public_key, operator.canonical(value).encode())
    return dict(state='RECOVERY_KEY_GENERATED_OFFLINE', recovery_key_sha256=operator.digest(value),
                public_key_sha256=operator._fingerprint(public))


def sign(private_key, public_key, plan_file, output):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import load_pem_private_key, Encoding, PublicFormat
    from src.review.recognition import runtime_governance_recovery as recovery
    private_key = operator._outside_repository(private_key)
    operator._protected(private_key, private=True)
    key_scope = recovery.validate_key(_read(public_key))
    plan = recovery.validate_plan(_read(plan_file))
    operator.require(plan['recovery_key_sha256'] == operator.digest(key_scope)
        and all(plan['scope'][k] == key_scope[k] for k in ('installation_id', 'owner_id')))
    output = operator._path(output)
    operator.require(not output.exists() and private_key.stat().st_size <= 65536)
    print(operator.canonical(dict(plan_sha256=operator.digest(plan),
        old_public_key_sha256=recovery.fingerprint(plan['old_root']),
        new_public_key_sha256=recovery.fingerprint(plan['new_root']))))
    operator.require(input('Type the reviewed exact cutover plan SHA256: ') == operator.digest(plan))
    key = load_pem_private_key(private_key.read_bytes(), password=operator._password())
    operator.require(isinstance(key, Ed25519PrivateKey)
        and key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw) == recovery._public(key_scope['public_key']))
    # Use the same actual UTC clock as the maintenance verifier; caller time is
    # never accepted as authorization or as a historical-key selector.
    from src.review.recognition import administration as a
    stamp = recovery._now()
    operator.require(a.timestamp(plan['created_at_utc']) <= a.timestamp(stamp) < a.timestamp(plan['expires_at_utc']))
    envelope = dict(serialized_approval=operator.canonical(plan),
                    signature=base64.b64encode(key.sign(recovery.signing_bytes(plan))).decode())
    recovery._verify_signature(key_scope, plan, envelope)
    operator._publish(output, operator.canonical(envelope).encode())
    return dict(state='RECOVERY_CUTOVER_SIGNED_OFFLINE', plan_sha256=operator.digest(plan))


class _Parser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, 'Invalid governance recovery arguments; use --help.\n')


def main(argv=None):
    parser = _Parser(description=__doc__)
    commands = parser.add_subparsers(dest='action', required=True, parser_class=_Parser)
    generate = commands.add_parser('keygen')
    for name in ('private-key', 'public-key'):
        generate.add_argument('--'+name, type=Path, required=True)
    generate.add_argument('--installation-id', required=True)
    generate.add_argument('--owner-id', type=int, required=True)
    generate.add_argument('--confirm-offline', action='store_true', required=True)
    signer = commands.add_parser('sign-cutover')
    for name in ('private-key', 'public-key', 'plan', 'output'):
        signer.add_argument('--'+name, type=Path, required=True)
    for action in ('request-enrollment', 'enroll', 'plan', 'cutover', 'inspect', 'publish-committed'):
        command = commands.add_parser(action)
        for name in ('target', 'control', 'key-file'):
            command.add_argument('--'+name, type=Path, required=True)
        command.add_argument('--installation-id', required=True)
        command.add_argument('--owner-id', type=int, required=True)
        command.add_argument('--original-public-key-sha256', required=True)
        if action == 'request-enrollment':
            command.add_argument('--recovery-public-key', type=Path, required=True)
            command.add_argument('--reason', required=True)
            command.add_argument('--output', type=Path, required=True)
        elif action == 'enroll':
            command.add_argument('--request-id', required=True)
            command.add_argument('--approved-request-sha256', required=True)
        elif action == 'plan':
            command.add_argument('--new-public-root', type=Path, required=True)
            command.add_argument('--reason', required=True)
            command.add_argument('--output', type=Path, required=True)
        elif action == 'cutover':
            command.add_argument('--authorization', type=Path, required=True)
            command.add_argument('--approved-plan-sha256', required=True)
        elif action == 'publish-committed':
            command.add_argument('--id', required=True)
    args = parser.parse_args(argv)
    try:
        if args.action == 'keygen':
            result = keygen(args.private_key, args.public_key, args.installation_id, args.owner_id)
        elif args.action == 'sign-cutover':
            result = sign(args.private_key, args.public_key, args.plan, args.output)
        else:
            # Supported production loader precedes ANY SQLite-dependent project
            # import on host operations. Offline operations never use PA files.
            from src.api.sqlite_runtime import load_production_sqlite
            load_production_sqlite()
            from src.review.recognition import administration as a, runtime_governance_recovery as recovery
            config = a.LocalAdministration(args.target, args.control, args.key_file)
            original = recovery._original(config)
            operator.require(original['installation_id'] == args.installation_id
                and original['owner_id'] == args.owner_id
                and recovery.fingerprint(original) == args.original_public_key_sha256)
            if hasattr(args, 'output'):
                operator._path(args.output); operator._protected(args.output.parent)
                operator.require(not args.output.exists() and not args.output.is_symlink())
            if args.action == 'request-enrollment':
                result = recovery.request_enrollment(config, _read(args.recovery_public_key), reason=args.reason)
            elif args.action == 'enroll':
                operator.require(input('Type the reviewed enrollment request SHA256: ') == args.approved_request_sha256)
                email = _secret('Email recovery challenge (hidden): ')
                code = _secret('Fresh authenticator code (hidden): ')
                result = recovery.enroll(config, args.request_id, email_challenge=email, code=code,
                                         approved_request_sha256=args.approved_request_sha256)
            elif args.action == 'plan':
                result = recovery.plan(config, _read(args.new_public_root), reason=args.reason)
            elif args.action == 'cutover':
                operator.require(input('Type the exact signed cutover plan SHA256: ') == args.approved_plan_sha256)
                result = recovery.cutover(config, _read(args.authorization), approved_plan_sha256=args.approved_plan_sha256)
            elif args.action == 'publish-committed':
                result = recovery.publish_committed(config, args.id)
            else:
                result = recovery.inspect(config)
            if hasattr(args, 'output'):
                value = result['plan'] if args.action == 'plan' else result
                operator._publish(args.output, operator.canonical(value).encode())
        print(operator.canonical(result))
        return 0
    except Exception:
        print(operator.canonical(dict(error='governance_recovery_outcome_unconfirmed',
            inspect_before_retry=True, execution_authority=False)), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

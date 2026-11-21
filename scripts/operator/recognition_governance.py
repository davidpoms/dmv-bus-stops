"""Explicit offline governance bootstrap/signing and public-only root installation.

Only pure serialization/signing contracts are imported; no SQLite, network,
authentication, migration or activation operations. Nothing happens on import.
"""

import argparse
import base64
from datetime import datetime, timezone
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
from uuid import UUID
import warnings

REPOSITORY = Path(__file__).resolve().parents[2]
if str(REPOSITORY) not in sys.path:
    sys.path.insert(0,str(REPOSITORY))
from src.review.recognition.rules import canonical, digest

# Pinned existing contracts, tested against the application verifier. Keeping
# these literals avoids importing sqlite3-dependent runtime modules on PA.
FORMAT = 'recognition-runtime-production-governance-v1'
MANDATE = 'dmv-bus-stops-g1-governance-mandate-4e-20-G13-v1'
DOMAIN = b'DMV-runtime-production-governance-v1\x00'
PACKAGE = 'recognition-preactivation-event-foundation-v1'
POLICY = '5a0112a24ba81c7067c4af2cf3ea6cda39d4fde5ee04f8591e81f152162d9cfd'
RUNTIME_PACKAGE = 'recognition-preactivation-runtime-foundation-v2'
RUNTIME_POLICY = '00194be45a1660e7890854caa4ed4a05a5cf79bbcb46e2e2163da64561e673b0'
ADMIN_SECONDS = 600
PREVIEW = 'target_event_foundation_preview'
COMPLETE = 'target_event_foundation_completion'


class SecureTerminalRequired(ValueError):
    """A secure prompt is unavailable; never fall back to echoed input."""


def require(condition):
    if not condition:
        raise ValueError('governance_bootstrap_rejected')


def fields(value,names):
    require(type(value) is dict and set(value) == set(names.split()))


def _object(pairs):
    result = {}
    for key,value in pairs:
        require(key not in result)
        result[key] = value
    return result


def _path(path):
    path = Path(path)
    require(path.is_absolute() and not path.is_symlink() and path.parent.resolve() == path.parent)
    return path


def _protected(path, *, private=False):
    path = _path(path)
    info = path.lstat()
    require((stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode))
            and (not path.is_file() or info.st_nlink == 1))
    if os.name == 'nt':
        # Check metadata only. Inherited permissions are acceptable only when all
        # allowed principals are the operator, SYSTEM or local Administrators.
        command = r'''
$ErrorActionPreference='Stop'
$acl=Get-Acl -LiteralPath $env:DMV_GOVERNANCE_ACL_PATH
$sid=[System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$owners=@($sid,'S-1-5-18','S-1-5-32-544')
$ok=$acl.GetOwner([System.Security.Principal.SecurityIdentifier]).Value -in $owners
# OWNER RIGHTS and CREATOR OWNER apply only to the already-checked owner.
$allowed=$owners+@('S-1-3-4','S-1-3-0')
foreach($rule in $acl.GetAccessRules($true,$true,[System.Security.Principal.SecurityIdentifier])) {
 if($rule.AccessControlType -eq 'Allow' -and $rule.IdentityReference.Value -notin $allowed) {$ok=$false}
}
if($ok){'PASS'}else{'FAIL'}
'''
        result = subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',command],
            env=dict(os.environ,DMV_GOVERNANCE_ACL_PATH=str(path)),capture_output=True,text=True,timeout=20)
        require(result.returncode == 0 and result.stdout.strip() == 'PASS')
    else:
        require(info.st_mode & (0o077 if private else 0o022) == 0)
        if private:
            require(info.st_uid == os.geteuid())


def _outside_repository(path):
    path = _path(path)
    require(not path.is_relative_to(REPOSITORY))
    require(not any((parent/'.git').exists() for parent in path.parents))
    _protected(path.parent,private=True)
    return path


def _read(path):
    path = _path(path)
    require(stat.S_ISREG(path.lstat().st_mode) and path.stat().st_nlink == 1)
    with path.open('r',encoding='utf-8') as handle:
        raw = handle.read(131073)
    require(len(raw.encode('utf-8')) <= 131072)
    value = json.loads(raw,object_pairs_hook=_object,parse_constant=lambda _: require(False))
    return value,raw


def _root(path):
    value,raw = _read(path)
    fields(value,'format mandate installation_id owner_id public_key')
    require(raw == canonical(value) and value['format'] == FORMAT and value['mandate'] == MANDATE)
    require(type(value['owner_id']) is int and value['owner_id'] > 0
            and str(UUID(value['installation_id'])) == value['installation_id'])
    public = base64.b64decode(value['public_key'],validate=True)
    require(len(public) == 32 and base64.b64encode(public).decode('ascii') == value['public_key'])
    return value,public


def _fingerprint(public):
    return hashlib.sha256(public).hexdigest()


def _publish(path, data, *, private=False):
    """Full file first, exclusive atomic publication; never replaces a file."""
    path = _outside_repository(path) if private else _path(path)
    _protected(path.parent,private=private)
    require(not path.exists() and not path.is_symlink())
    fd,name = tempfile.mkstemp(prefix='.'+path.name+'.',dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd,'wb') as handle:
            handle.write(data);handle.flush();os.fsync(handle.fileno())
        _protected(temporary,private=private)
        os.link(temporary,path)  # Exclusive; existing destination/symlink rejects.
    finally:
        temporary.unlink(missing_ok=True)
    _protected(path,private=private)
    if os.name != 'nt':
        directory = os.open(path.parent,os.O_RDONLY | os.O_DIRECTORY)
        try:os.fsync(directory)
        finally:os.close(directory)


def _windows_console_available():
    # Query handles only: never allocate a console, change echo mode, or read input.
    import ctypes
    kernel = ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.GetStdHandle.argtypes = [ctypes.c_uint32]
    kernel.GetStdHandle.restype = ctypes.c_void_p
    kernel.GetConsoleMode.argtypes = [ctypes.c_void_p,ctypes.POINTER(ctypes.c_uint32)]
    kernel.GetConsoleMode.restype = ctypes.c_int
    mode = ctypes.c_uint32()
    return all(kernel.GetConsoleMode(kernel.GetStdHandle(handle & 0xffffffff),ctypes.byref(mode))
               for handle in (-10,-11))  # STD_INPUT_HANDLE, STD_OUTPUT_HANDLE


def _password(confirm=False):
    # Never accept passphrases through argv/environment or echo fallback.
    if os.name == 'nt' and not _windows_console_available():
        raise SecureTerminalRequired('governance_secure_terminal_required')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error',getpass.GetPassWarning)
            value = getpass.getpass('Governance key passphrase (not echoed): ')
            require(len(value) >= 12)
            if confirm:
                require(value == getpass.getpass('Repeat passphrase (not echoed): '))
    except (getpass.GetPassWarning,OSError,EOFError):
        # Windows getpass uses console APIs; captured executions may raise an
        # invalid-handle error before even rendering the first prompt. Do not
        # expose the original error/args, which could contain sensitive data.
        raise SecureTerminalRequired('governance_secure_terminal_required') from None
    return value.encode('utf-8')


def keygen(private_key,public_root,installation_id,owner_id):
    private_key = _outside_repository(private_key)
    public_root = _path(public_root)
    require(private_key != public_root and not private_key.exists() and not public_root.exists())
    _protected(public_root.parent)
    require(type(owner_id) is int and owner_id > 0 and str(UUID(installation_id)) == installation_id)
    password = _password(confirm=True)
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat,PrivateFormat,BestAvailableEncryption
    key = Ed25519PrivateKey.generate()
    public = key.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw)
    root = dict(format=FORMAT,mandate=MANDATE,installation_id=installation_id,owner_id=owner_id,
                public_key=base64.b64encode(public).decode('ascii'))
    _publish(private_key,key.private_bytes(Encoding.PEM,PrivateFormat.PKCS8,BestAvailableEncryption(password)),private=True)
    _publish(public_root,canonical(root).encode('utf-8'))
    return dict(state='GENERATED_OFFLINE',public_key_sha256=_fingerprint(public))


def _payload(path,root):
    body,_ = _read(path)
    fields(body,'format mandate installation_id binding_sha256 holder subject target control issued_at_utc expires_at_utc approvals')
    require(body['format'] == root['format'] and body['mandate'] == root['mandate']
            and body['installation_id'] == root['installation_id'])
    from src.review.recognition import runtime_profile_successor_contract as successor
    if body.get('subject', {}).get('kind') in successor.PURPOSES:
        successor.validate_envelope(body, root)
        _fresh(body)
        return body
    fields(body['holder'],'actor_id primary_sha256 session_sha256')
    require(type(body['holder']['actor_id']) is int and body['holder']['actor_id'] == root['owner_id'])
    for value in (body['binding_sha256'],body['holder']['primary_sha256'],body['holder']['session_sha256']):
        require(type(value) is str and re.fullmatch('[0-9a-f]{64}',value) is not None)
    for physical in (body['target'],body['control']):
        fields(physical,'hostname database device inode')
        require(all(type(physical[k]) is str and physical[k] for k in ('hostname','database'))
                and all(type(physical[k]) is int and physical[k] >= 0 for k in ('device','inode')))
    subject = body['subject']
    require(type(subject) is dict)
    package, policy = PACKAGE, POLICY
    if subject.get('kind') == PREVIEW:
        fields(subject,'kind operator reason package' if 'package' in subject else 'kind operator reason')
        if 'package' in subject:
            require(subject['package'] == RUNTIME_PACKAGE)
            package, policy = RUNTIME_PACKAGE, RUNTIME_POLICY
        for key,limit in (('operator',200),('reason',2000)):
            require(type(subject[key]) is str and 1 <= len(subject[key]) <= limit and '\x00' not in subject[key])
        binding = dict(permission='inspection',action='preview',operation_sha256=digest(subject),policy_sha256=policy)
    else:
        fields(subject,'kind plan')
        require(subject['kind'] == COMPLETE and type(subject['plan']) is dict)
        plan = subject['plan']
        if plan['package'] == RUNTIME_PACKAGE:
            package, policy = RUNTIME_PACKAGE, RUNTIME_POLICY
        require(plan['package'] == package and type(plan['generation']) is int and plan['generation'] in (5,6)
                and plan['binding_sha256'] == body['binding_sha256']
                and plan['installation_id'] == body['installation_id'] and plan['owner_id'] == body['holder']['actor_id']
                and plan['physical'] == dict(target=body['target'],control=body['control']))
        binding = dict(permission='migration',action='install',operation_sha256=policy,policy_sha256=policy)
    expected = dict(target=body['target'],environment='production',family=package,population_sha256=None,
                    reference=MANDATE,expires_at_utc=body['expires_at_utc'],**binding)
    require(canonical(body['approvals']) == canonical([expected]))
    require(len(canonical(body).encode('utf-8')) <= 65536)
    _fresh(body)
    return body


def _fresh(body):
    def instant(text):
        parsed = datetime.strptime(text,'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
        require(parsed.strftime('%Y-%m-%dT%H:%M:%SZ') == text)
        return parsed.timestamp()
    issued,expires = instant(body['issued_at_utc']),instant(body['expires_at_utc'])
    require(issued <= datetime.now(timezone.utc).timestamp() < expires <= issued+ADMIN_SECONDS)


def sign(private_key,public_root,payload,output):
    private_key = _outside_repository(private_key)
    _protected(private_key,private=True)
    root,public = _root(public_root)
    body = _payload(payload,root)
    output = _path(output)
    require(not output.exists() and not output.is_symlink())
    print(canonical(dict(purpose=body['subject']['kind'],payload_sha256=digest(body),public_key_sha256=_fingerprint(public))))
    require(input('Type the reviewed payload SHA256 to sign only this request: ') == digest(body))
    from cryptography.hazmat.primitives.serialization import load_pem_private_key,Encoding,PublicFormat
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    with private_key.open('rb') as handle:data = handle.read(65537)
    require(len(data) <= 65536 and data.startswith(b'-----BEGIN ENCRYPTED PRIVATE KEY-----'))
    key = load_pem_private_key(data,password=_password())
    require(isinstance(key,Ed25519PrivateKey) and key.public_key().public_bytes(Encoding.Raw,PublicFormat.Raw) == public)
    _fresh(body)
    serialized = canonical(body)
    signature = key.sign(DOMAIN+serialized.encode('utf-8'))
    key.public_key().verify(signature,DOMAIN+serialized.encode('utf-8'))
    _publish(output,canonical(dict(serialized_approval=serialized,signature=base64.b64encode(signature).decode('ascii'))).encode('utf-8'))
    return dict(state='SIGNED_OFFLINE',payload_sha256=digest(body),public_key_sha256=_fingerprint(public))


def successor_payload(public_root, purpose, authorization_id, output, source=None, operator=None, reason=None):
    """Build public, reviewable custodian payloads only. No signing or networking."""
    from src.review.recognition import runtime_profile_successor_contract as successor
    root, _ = _root(public_root)
    require(purpose in ('prepare','complete','inspect'))
    kinds = dict(prepare=successor.PREPARE,complete=successor.COMPLETE,inspect=successor.INSPECT)
    if purpose == 'inspect':
        require(source is None and operator is None and reason is None)
        subject = dict(kind=kinds[purpose], authorization_id=authorization_id)
    else:
        require(source is not None)
        data, _ = _read(source)
        if purpose == 'prepare':
            subject = dict(kind=kinds[purpose], authorization_id=authorization_id,
                           scope=data['scope'],operator=operator,reason=reason)
        else:
            require(operator is None and reason is None and data['plan']['authorization_id'] == authorization_id)
            subject = dict(kind=kinds[purpose],plan=data['plan'])
    now = datetime.now(timezone.utc).replace(microsecond=0)
    from datetime import timedelta
    expires = now+timedelta(seconds=ADMIN_SECONDS)
    if purpose == 'complete':
        expires = min(expires,datetime.strptime(subject['plan']['deadline_at_utc'],'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc))
    body = dict(format=FORMAT,mandate=MANDATE,installation_id=root['installation_id'],
        binding_sha256=successor.SOURCE_BINDING,holder=dict(kind='governance_custodian',actor_id=root['owner_id']),
        subject=subject,**successor.destination(),issued_at_utc=now.strftime('%Y-%m-%dT%H:%M:%SZ'),
        expires_at_utc=expires.strftime('%Y-%m-%dT%H:%M:%SZ'))
    body['approvals'] = [successor.approval(subject,body['target'],body['expires_at_utc'],MANDATE)]
    successor.validate_envelope(body,root);_fresh(body)
    _publish(_path(output),canonical(body).encode('utf-8'))
    return dict(state='PAYLOAD_PREPARED',payload_sha256=digest(body),execution_authority=False)


def install_public_root(source,control,installation_id,owner_id,approved_public_key_sha256):
    control = _path(control)
    require(stat.S_ISREG(control.lstat().st_mode) and control.stat().st_nlink == 1)
    _protected(control.parent)
    root,public = _root(source)
    require(root['installation_id'] == installation_id and root['owner_id'] == owner_id
            and _fingerprint(public) == approved_public_key_sha256)
    require(input('Type the approved public-key SHA256 to install only the public root: ') == approved_public_key_sha256)
    destination = control.with_name(control.name+'.governance-root.json')
    _publish(destination,canonical(root).encode('utf-8'))
    installed,checked = _root(destination)
    require(installed == root and checked == public)
    return dict(state='PUBLIC_ROOT_INSTALLED',public_key_sha256=_fingerprint(public))


class _Parser(argparse.ArgumentParser):
    def error(self,message):self.exit(2,'Invalid governance operator arguments; use --help.\n')


def main(argv=None):
    parser = _Parser(description=__doc__)
    commands = parser.add_subparsers(dest='action',required=True)
    generate = commands.add_parser('keygen')
    generate.add_argument('--private-key',type=Path,required=True)
    generate.add_argument('--public-root',type=Path,required=True)
    generate.add_argument('--installation-id',required=True)
    generate.add_argument('--owner-id',type=int,required=True)
    generate.add_argument('--confirm-offline',action='store_true',required=True)
    signing = commands.add_parser('sign')
    for name in ('private-key','public-root','payload','output'):signing.add_argument('--'+name,type=Path,required=True)
    signing.add_argument('--confirm-offline',action='store_true',required=True)
    successor = commands.add_parser('successor-payload')
    successor.add_argument('--public-root',type=Path,required=True)
    successor.add_argument('--purpose',choices=('prepare','complete','inspect'),required=True)
    successor.add_argument('--authorization-id',required=True)
    successor.add_argument('--source',type=Path)
    successor.add_argument('--operator')
    successor.add_argument('--reason')
    successor.add_argument('--output',type=Path,required=True)
    install = commands.add_parser('install-public-root')
    install.add_argument('--source',type=Path,required=True)
    install.add_argument('--control',type=Path,required=True)
    install.add_argument('--installation-id',required=True)
    install.add_argument('--owner-id',type=int,required=True)
    install.add_argument('--approved-public-key-sha256',required=True)
    args = vars(parser.parse_args(argv));action = args.pop('action');args.pop('confirm_offline',None)
    try:
        result = dict(keygen=keygen,sign=sign,**{'install-public-root':install_public_root,
                      'successor-payload':successor_payload})[action](**args)
        print(canonical(result));return 0
    except SecureTerminalRequired:
        print(canonical(dict(error='governance_secure_terminal_required',
            action='run_in_interactive_terminal',inspect_outputs_before_retry=True)),file=sys.stderr)
        return 1
    except Exception:
        print(canonical(dict(error='governance_bootstrap_failed',inspect_outputs_before_retry=True)),file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

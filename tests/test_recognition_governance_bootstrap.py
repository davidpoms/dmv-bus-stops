"""Synthetic keys live only in external temporary directories, never the checkout."""

from contextlib import redirect_stdout
from dataclasses import asdict
from datetime import datetime,timedelta,timezone
import base64
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts.operator import recognition_governance as tool
from src.review.recognition import runtime_production_governance as governance
from src.review.recognition import runtime_target_schema_completion as completion
from src.review.recognition import runtime_target_schema_lineage as lineage
from src.review.recognition import runtime_finalization_contract as contract, authorization, event_schema
from src.review.recognition import admin_auth
from src.review.recognition.rules import canonical,digest


class GovernanceBootstrapTests(unittest.TestCase):
    def setUp(self):
        # Unit-test interactive success with synthetic passphrases; captured/native
        # Windows rejection is exercised separately below without generating keys.
        self.enterContext(patch.object(tool,'_windows_console_available',return_value=True))
        self.workspace=self.enterContext(tempfile.TemporaryDirectory(prefix='governance-operator-test-'))
        self.base=Path(self.workspace).resolve()
        self.operator=self.base/'operator';self.operator.mkdir(mode=0o700)
        self.runtime=self.base/'runtime';self.runtime.mkdir(mode=0o700)
        self.private=self.operator/'operator-key.pem';self.public=self.operator/'public-root.json'
        self.installation='f5d48fcd-a8ce-45fb-ad5c-0009acaa7947'
        self.password='synthetic-test-passphrase'
        with patch.object(tool.getpass,'getpass',return_value=self.password):
            self.generated=tool.keygen(self.private,self.public,self.installation,144)
        self.control=self.runtime/'recognition-admin-control.db';self.control.touch()
        self.target=self.runtime/'target.db';self.target.touch()
        self.config=SimpleNamespace(control=self.control,target=self.target)

    def install(self):
        fingerprint=self.generated['public_key_sha256']
        with patch('builtins.input',return_value=fingerprint):
            return tool.install_public_root(self.public,self.control,self.installation,144,fingerprint)

    def body(self):
        now=datetime.now(timezone.utc).replace(microsecond=0)
        stamp=lambda dt:dt.strftime('%Y-%m-%dT%H:%M:%SZ')
        subject=dict(kind=completion.PREVIEW_KIND,operator='synthetic-owner',reason='synthetic preview')
        grant=authorization.Authorization(target=authorization.target_identity(self.target),environment='production',
            expires_at_utc=stamp(now+timedelta(seconds=300)),**completion.preview_binding(subject))
        return dict(format=governance.FORMAT,mandate=contract.MANDATE,installation_id=self.installation,
            binding_sha256='a'*64,holder=dict(actor_id=144,primary_sha256='b'*64,session_sha256='c'*64),
            subject=subject,target=asdict(authorization.target_identity(self.target)),
            control=asdict(authorization.target_identity(self.control)),issued_at_utc=stamp(now),
            expires_at_utc=grant.expires_at_utc,approvals=[asdict(grant)])

    def test_generated_public_root_exact_existing_verifier_and_permissions(self):
        root,public=tool._root(self.public)
        self.assertEqual(32,len(public))
        self.assertEqual({'format','mandate','installation_id','owner_id','public_key'},set(root))
        self.assertEqual(canonical(root),self.public.read_text())
        self.assertFalse(self.public.read_bytes().endswith(b'\n'))
        self.assertEqual(governance.FORMAT,tool.FORMAT);self.assertEqual(governance.DOMAIN,tool.DOMAIN)
        self.assertEqual(contract.MANDATE,tool.MANDATE);self.assertEqual(digest(event_schema.definitions()),tool.POLICY)
        self.assertEqual(lineage.RUNTIME_PACKAGE, tool.RUNTIME_PACKAGE)
        self.assertEqual(digest(lineage.package_definitions(lineage.RUNTIME_PACKAGE)), tool.RUNTIME_POLICY)
        self.assertEqual(admin_auth.RECENT_SECONDS,tool.ADMIN_SECONDS)
        self.assertEqual(self.generated['public_key_sha256'],tool._fingerprint(public))
        result=self.install();self.assertEqual('PUBLIC_ROOT_INSTALLED',result['state'])
        self.assertEqual(root,governance._root(self.config))
        self.assertEqual(root,lineage._protected_root(self.config))
        if os.name != 'nt':self.assertEqual(0o600,self.private.stat().st_mode & 0o777)
        tool._protected(self.private,private=True)

    def test_private_is_encrypted_external_and_absent_from_runtime_artifact(self):
        self.install()
        require=lambda condition:self.assertTrue(condition,'private-key separation failed')
        require(not self.private.is_relative_to(tool.REPOSITORY))
        require(self.private.read_bytes().startswith(b'-----BEGIN ENCRYPTED PRIVATE KEY-----'))
        from cryptography.hazmat.primitives.serialization import load_pem_private_key
        with self.assertRaises(TypeError):load_pem_private_key(self.private.read_bytes(),password=None)
        for path in self.runtime.iterdir():
            if path.is_file():
                require(path.read_bytes() != self.private.read_bytes())
                require(b'PRIVATE KEY' not in path.read_bytes())
        # Reject another Git repository as well as this checkout, before generation.
        other=self.base/'other-repo';other.mkdir();(other/'.git').mkdir()
        for path in (tool.REPOSITORY/'never-create.pem',other/'never-create.pem'):
            with patch('cryptography.hazmat.primitives.asymmetric.ed25519.Ed25519PrivateKey.generate') as generate:
                with self.assertRaises(ValueError):tool.keygen(path,self.operator/'unused.json',self.installation,144)
                generate.assert_not_called()
            self.assertFalse(path.exists())

    def test_generated_signature_verifies_existing_production_verifier(self):
        self.install();body=self.body();body['subject']['reason']='review \u2603'
        body['approvals']=[asdict(authorization.Authorization(target=authorization.Target(**body['target']),
            environment='production',expires_at_utc=body['expires_at_utc'],**completion.preview_binding(body['subject'])))]
        payload=self.operator/'reviewed.json';payload.write_text(json.dumps(body,ensure_ascii=False),encoding='utf-8')
        output=self.operator/'signed.json'
        with patch('builtins.input',return_value=digest(body)),patch.object(tool.getpass,'getpass',return_value=self.password),redirect_stdout(io.StringIO()) as logs:
            result=tool.sign(self.private,self.public,payload,output)
        envelope=json.loads(output.read_text())
        self.assertEqual({'serialized_approval','signature'},set(envelope))
        self.assertEqual(canonical(body),envelope['serialized_approval'])
        self.assertEqual(64,len(base64.b64decode(envelope['signature'])))
        _,checked,_=governance._verify(self.config,envelope['serialized_approval'],envelope['signature'])
        self.assertEqual(body,checked);self.assertEqual('SIGNED_OFFLINE',result['state'])
        self.assertNotIn(self.password,logs.getvalue());self.assertNotIn('PRIVATE KEY',logs.getvalue())
        tool._protected(output)

    def test_v2_preview_signature_uses_existing_verifier_and_distinct_closed_policy(self):
        self.install(); body = self.body()
        body['subject']['package'] = lineage.RUNTIME_PACKAGE
        body['approvals'] = [asdict(authorization.Authorization(target=authorization.Target(**body['target']),
            environment='production',expires_at_utc=body['expires_at_utc'],**completion.preview_binding(body['subject'])))]
        payload = self.operator/'reviewed-v2.json'; payload.write_text(canonical(body))
        output = self.operator/'signed-v2.json'
        with patch('builtins.input',return_value=digest(body)),patch.object(tool.getpass,'getpass',return_value=self.password),redirect_stdout(io.StringIO()):
            tool.sign(self.private,self.public,payload,output)
        artifact = json.loads(output.read_text())
        self.assertEqual(body,governance._verify(self.config,**dict(serialized=artifact['serialized_approval'],signature=artifact['signature']))[1])

    def test_installer_wrong_scope_fingerprint_and_existing_file_reject(self):
        fingerprint=self.generated['public_key_sha256']
        for installation,owner,sha in (('aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',144,fingerprint),
                                        (self.installation,1,fingerprint),(self.installation,144,'0'*64)):
            with self.subTest(owner=owner,sha=sha),self.assertRaises(ValueError):
                tool.install_public_root(self.public,self.control,installation,owner,sha)
        self.install()
        before=governance.trust_path(self.config).read_bytes()
        with self.assertRaises(ValueError):self.install()
        self.assertTrue(before == governance.trust_path(self.config).read_bytes())

    def test_noncanonical_symlink_hardlink_and_unprotected_inputs_reject(self):
        original=self.public.read_text()
        self.public.write_text(original+'\n')
        with self.assertRaises(ValueError):self.install()
        self.public.write_text(original)
        link=self.operator/'linked.json';os.link(self.public,link)
        with self.assertRaises(ValueError):self.install()
        link.unlink()
        if os.name != 'nt':
            self.runtime.chmod(0o777)
            try:
                with self.assertRaises(ValueError):self.install()
            finally:self.runtime.chmod(0o700)
        try:
            symlink=self.operator/'symlink.json';symlink.symlink_to(self.public)
        except OSError:
            return  # Platform denies symlink creation; hard-link check still ran.
        with self.assertRaises(ValueError):tool._root(symlink)

    def test_reject_unsigned_wrong_purpose_and_output_overwrite(self):
        body=self.body();body['subject']['kind']='issuer'
        payload=self.operator/'bad.json';payload.write_text(canonical(body))
        with self.assertRaises(ValueError):tool.sign(self.private,self.public,payload,self.operator/'not-written.json')
        self.assertFalse((self.operator/'not-written.json').exists())
        payload.write_text(canonical(self.body()))
        with patch('builtins.input',return_value='wrong'),self.assertRaises(ValueError):
            tool.sign(self.private,self.public,payload,self.operator/'not-written.json')
        with self.assertRaises(ValueError):tool.keygen(self.private,self.public,self.installation,144)

    def test_import_and_public_install_do_not_import_sqlite_or_private_crypto(self):
        code=r'''
import sys,tempfile
from pathlib import Path
from scripts.operator import recognition_governance
assert all(Path(p).resolve().is_relative_to(Path(tempfile.gettempdir()).resolve()) for p in sys.argv[1:3])
fingerprint=sys.argv[3]
import builtins
builtins.input=lambda _:fingerprint
recognition_governance.install_public_root(Path(sys.argv[1]),Path(sys.argv[2]),
    'f5d48fcd-a8ce-45fb-ad5c-0009acaa7947',144,fingerprint)
assert 'sqlite3' not in sys.modules
assert 'cryptography.hazmat.primitives.asymmetric.ed25519' not in sys.modules
assert 'src.review.recognition.runtime_production_governance' not in sys.modules
print('PASS')
'''
        result=subprocess.run([sys.executable,'-B','-c',code,str(self.public),str(self.control),
                               self.generated['public_key_sha256']],capture_output=True,text=True,timeout=30)
        self.assertEqual(0,result.returncode,result.stderr);self.assertEqual('PASS',result.stdout.strip())
        with patch('sys.stderr',new_callable=io.StringIO) as errors,self.assertRaises(SystemExit):
            tool.main(['keygen','--passphrase','SENTINEL-NEVER-ECHO'])
        self.assertNotIn('SENTINEL-NEVER-ECHO',errors.getvalue())

    def test_publication_failure_leaves_no_partial_public_root(self):
        before={p.name for p in self.runtime.iterdir()}
        with patch.object(tool.os,'link',side_effect=OSError('synthetic publication failure')),self.assertRaises(OSError):
            self.install()
        self.assertEqual(before,{p.name for p in self.runtime.iterdir()})
        self.assertFalse(governance.trust_path(self.config).exists())

    def test_broad_directory_permissions_rejected_without_any_key_in_directory(self):
        unsafe=self.base/'empty-unsafe';unsafe.mkdir(mode=0o700)
        if os.name == 'nt':
            result=subprocess.run(['icacls.exe',str(unsafe),'/grant','*S-1-1-0:(OI)(CI)R'],
                                  capture_output=True,text=True,timeout=20)
            self.assertEqual(0,result.returncode,'Could not configure disposable ACL test')
        else:unsafe.chmod(0o777)
        with self.assertRaises(ValueError):tool._protected(unsafe,private=True)
        self.assertFalse(list(unsafe.iterdir()))

    def test_cli_interactive_keygen_retains_encryption_and_canonical_root(self):
        private=self.operator/'second-test-key.pem';public=self.operator/'second-test-root.json'
        with (patch.object(tool.getpass,'getpass',return_value=self.password),
              patch('sys.stdout',new_callable=io.StringIO) as output):
            status=tool.main(['keygen','--private-key',str(private),'--public-root',str(public),
                '--installation-id',self.installation,'--owner-id','144','--confirm-offline'])
        self.assertEqual(0,status)
        self.assertEqual('GENERATED_OFFLINE',json.loads(output.getvalue())['state'])
        root,_=tool._root(public)
        self.assertEqual(canonical(root),public.read_text())
        self.assertTrue(private.read_bytes().startswith(b'-----BEGIN ENCRYPTED PRIVATE KEY-----'))
        self.assertNotIn(self.password,output.getvalue())
        tool._protected(private,private=True)


class SecurePromptTests(unittest.TestCase):
    def test_missing_console_is_classified_without_key_generation_or_outputs(self):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        sentinel='SENTINEL-SECRET-DO-NOT-LOG'
        with tempfile.TemporaryDirectory(prefix='governance-prompt-test-') as folder:
            directory=Path(folder).resolve()
            private=directory/'not-created.pem';public=directory/'not-created.json'
            args=['keygen','--private-key',str(private),'--public-root',str(public),
                  '--installation-id','f5d48fcd-a8ce-45fb-ad5c-0009acaa7947','--owner-id','144','--confirm-offline']
            for error in (OSError(6,sentinel),EOFError(sentinel),tool.getpass.GetPassWarning(sentinel)):
                with (self.subTest(error=type(error).__name__),
                      patch.object(tool.getpass,'getpass',side_effect=error),
                      patch.object(tool,'_windows_console_available',return_value=True),
                      patch.object(Ed25519PrivateKey,'generate') as generate,
                      patch('sys.stdout',new_callable=io.StringIO) as output,
                      patch('sys.stderr',new_callable=io.StringIO) as errors):
                    self.assertEqual(1,tool.main(args))
                generate.assert_not_called()
                self.assertFalse(private.exists());self.assertFalse(public.exists())
                self.assertEqual('',output.getvalue())
                self.assertEqual('governance_secure_terminal_required',json.loads(errors.getvalue())['error'])
                self.assertNotIn(sentinel,errors.getvalue())

    def test_echo_fallback_is_still_rejected_before_plaintext_read(self):
        with (patch.object(tool.getpass,'getpass',tool.getpass.fallback_getpass),
              patch.object(tool,'_windows_console_available',return_value=True),
              patch.object(tool.getpass,'_raw_input') as raw,
              self.assertRaises(tool.SecureTerminalRequired)):
            tool._password(confirm=True)
        raw.assert_not_called()

    def test_short_or_mismatched_passphrases_still_reject(self):
        for values in (['short'],['synthetic-password-one','synthetic-password-two']):
            with (self.subTest(lengths=[len(v) for v in values]),
                  patch.object(tool,'_windows_console_available',return_value=True),
                  patch.object(tool.getpass,'getpass',side_effect=values),self.assertRaises(ValueError) as caught):
                tool._password(confirm=True)
            self.assertNotIsInstance(caught.exception,tool.SecureTerminalRequired)

    @unittest.skipUnless(os.name == 'nt','Windows getpass console routing')
    def test_real_windows_getpass_rejects_wrapped_stdin_without_reading_it(self):
        wrapped=io.StringIO('SENTINEL-NEVER-READ\n')
        with (patch('sys.stdin',wrapped),patch.object(tool,'_windows_console_available',return_value=True),
              self.assertRaises(tool.SecureTerminalRequired)):tool._password()
        self.assertEqual(0,wrapped.tell())

    @unittest.skipUnless(os.name == 'nt','Windows console preflight')
    def test_missing_console_rejects_before_attempting_prompt(self):
        with (patch.object(tool,'_windows_console_available',return_value=False),
              patch.object(tool.getpass,'getpass') as prompt,self.assertRaises(tool.SecureTerminalRequired)):
            tool._password(confirm=True)
        prompt.assert_not_called()

    @unittest.skipUnless(os.name == 'nt','Windows detached console execution')
    def test_real_windows_detached_process_reports_secure_terminal_required(self):
        # No keygen, files or human input: reproduce the captured execution surface.
        code=r'''
from scripts.operator import recognition_governance as tool
try:tool._password()
except tool.SecureTerminalRequired:print('SECURE_TERMINAL_REQUIRED')
else:raise AssertionError('Noninteractive password input unexpectedly accepted')
'''
        result=subprocess.run([sys.executable,'-B','-c',code],stdin=subprocess.DEVNULL,
            capture_output=True,text=True,timeout=15,creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(0,result.returncode)
        self.assertEqual('SECURE_TERMINAL_REQUIRED',result.stdout.strip())
        self.assertFalse(result.stderr)

"""R22 test-only fresh disposable bootstrap. No production enrollment or keys."""
from contextlib import contextmanager
from pathlib import Path
import tempfile
from unittest.mock import patch
from uuid import uuid4

from src.review.recognition import administration as a, authorization
from src.review.recognition import runtime_finalization_storage as storage
from src.review.recognition import runtime_decision_outcome_journal_schema as journal
from tests.recognition_authorization_fixture import approval


@contextmanager
def bootstrap():
    install = a.install
    def writable(suffix=None,prefix=None,dir=None):
        root=Path(__file__).resolve().parents[1]/('recognition-r22-'+uuid4().hex)
        root.mkdir(mode=0o777)
        return str(root)
    def prepared(config, **options):
        proof=approval(config.target,**authorization.migration_binding('runtime_finalization_target',journal.definitions('target')))
        with a.connect(config.target,write=True) as conn:
            conn.execute('BEGIN IMMEDIATE')
            storage.install_target(conn,approval=proof['authorization'],authority=proof['authority'])
            conn.commit()
        result=install(config,**options)
        proof=approval(config.control,**authorization.migration_binding('runtime_finalization_control',journal.definitions('control')))
        with a.connect(config.control,write=True) as conn:
            conn.execute('BEGIN IMMEDIATE')
            storage.install_control(conn,approval=proof['authorization'],authority=proof['authority'])
            conn.commit()
        return result
    with patch.object(tempfile,'mkdtemp',side_effect=writable),patch.object(a,'install',side_effect=prepared):
        yield


def governance(config,intent,policy):
    from src.review.recognition import runtime_finalization_contract as contract
    from src.review.recognition.rules import digest
    proofs={purpose:approval(config.target,family='runtime_finalization',permission='governance',action=purpose,
        operation_sha256=digest(intent),policy_sha256=digest(policy),population_sha256=None,reference=contract.MANDATE)
        for purpose in ('bind_governance','adopt_policy','appoint_issuer','authorize_issuer')}
    return dict(approvals={key:value['authorization'] for key,value in proofs.items()},
                authority=proofs['bind_governance']['authority'])

"""Exact R28 journal extension metadata. No authority or arbitrary package input."""
from . import runtime_decision_outcome_journal_schema as journal
from . import runtime_enrollment_transition_schema as transition
from .rules import digest
from .trust import require

MIGRATION = 'recognition-runtime-finalization-journal-extension-v1'
ACTION = 'runtime_finalization_journal_schema_installed'
PACKAGE = 'recognition-runtime-outcome-witness-storage-v1'
GUARD = transition.PLANS+'_source_guard'


def definitions():
    original=transition.definitions()[GUARD]
    predicate="json_extract(NEW.body_json,'$.migration_id')='"+transition.PACKAGE+"'"
    require(original.count(predicate)==1,'journal_original_guard_changed')
    # Only two fixed packages; every other original source predicate survives.
    updated=original.replace(predicate,'('+predicate+" OR json_extract(NEW.body_json,'$.migration_id')='"+PACKAGE+"')")
    return {**journal.definitions('control'),GUARD:updated}


def present(conn):
    return bool(conn.execute("SELECT 1 FROM recognition_admin_audit WHERE json_extract(body_json,'$.action')=? "
        "OR json_extract(body_json,'$.subject.migration_id')=?",(ACTION,MIGRATION)).fetchone())


class TargetPackage:
    TABLE=journal.WITNESSES
    PACKAGE=PACKAGE

    @staticmethod
    def definitions():return journal.definitions('target')

    @staticmethod
    def check_schema(conn):return journal.check_schema(conn,'target')


def plan_manifest(conn, plan, sequence, *, _edges=None):
    """Validate the full current lineage before selecting the original plan era."""
    from . import runtime_schema_package_lineage as lineage
    from . import runtime_execution_claim_schema as claims
    if not (present(conn) or lineage.present(conn)):return claims.manifest(conn)
    edges=lineage.verify(conn) if _edges is None else _edges
    ordered=sorted(edges.values(),key=lambda edge:edge['sequence'])
    objects=ordered[0]['before']
    for edge in ordered:
        if edge['sequence']>=sequence:break
        objects=edge['after']
    return digest(objects)


def migrate_control(config, *, expected_generation, approval, authority, operator, reason):
    """Fixed control extension before the existing target transition ceremony.

    No target DDL/DML, binding update, enrollment or recovery. An unknown commit
    requires durable inspection, not automatic continuation or another install.
    """
    from . import administration as a, administration_schema as base, authorization
    from . import runtime_validation as runtime, runtime_schema_package_lineage as lineage
    from . import runtime_execution_claim_schema as claims, local_readiness
    from dataclasses import asdict
    require(type(config) is a.LocalAdministration,'local_administration_required')
    config.paths();runtime.enrollment._text(operator,200);runtime.enrollment._text(reason,2000)
    with a.connect(config.control,write=True) as control:
        control.execute('BEGIN IMMEDIATE');base.check_control(control)
        binding,_,_=runtime._history(control)
        require(binding['generation']==expected_generation,'journal_generation_conflict')
        require(asdict(a.target_identity(control))==binding['control_identity'],'control_identity_mismatch')
        require(local_readiness._state(control,binding)['state'] in ('NOT_ACTIVATED','DEACTIVATED'),
                'journal_requires_inactive')
        transition.require_no_pending(control)
        with a.connect(config.target,write=True) as target:
            target.execute('BEGIN IMMEDIATE');target.execute('PRAGMA query_only=ON')
            a._verify(config,control,target,binding)
            authorization.verify(config.control,approval,authority,
                **authorization.migration_binding(MIGRATION,definitions()))
            if present(control):
                lineage.verify(control);control.rollback()
                return dict(installed=False,migration_id=MIGRATION)
            edges=lineage.verify(control)
            require({'A','T','E','L'}<=set(edges),'journal_predecessors_missing')
            require(not control.execute('SELECT 1 FROM '+transition.HISTORY+' WHERE state<>? AND sequence=4',('FINALIZED',)).fetchone(),
                    'journal_history_invalid')
            for table in ('recognition_runtime_execution_authorities','recognition_runtime_execution_attempts',
                          'recognition_runtime_execution_claims'):
                require(not control.execute('SELECT 1 FROM '+table).fetchone(),'journal_unsettled_runtime_work')
            require(not target.execute("SELECT 1 FROM sqlite_master WHERE name=?",(journal.WITNESSES,)).fetchone(),
                    'journal_target_already_installed')
            previous=claims.manifest(control);now=runtime._utc_now()
            control.execute('SAVEPOINT journal_extension')
            try:
                if approval.environment=='production':
                    from .runtime_production_governance import evidence
                    from .trust import load
                    proof=evidence(authority,approval)
                    actor=load(proof['serialized'])['holder']['actor_id']
                    a._audit(control,'runtime_production_schema_approval_verified',actor,now,
                             dict(approval=asdict(approval),governance_proof=proof))
                control.execute('DROP TRIGGER '+GUARD)
                for sql in definitions().values():control.execute(sql)
                a._audit(control,ACTION,operator,now,dict(migration_id=MIGRATION,
                    previous_schema_sha256=previous,installed_schema_sha256=claims.manifest(control),
                    installation_id=binding['installation_id'],generation=binding['generation'],reason=reason))
                base.check_control(control);lineage.verify(control)
                a._verify(config,control,target,binding)
                authorization.verify(config.control,approval,authority,
                    **authorization.migration_binding(MIGRATION,definitions()))
                require(target.total_changes==0 and target.execute('PRAGMA query_only').fetchone()[0]==1,
                        'journal_target_write_forbidden')
                control.execute('RELEASE journal_extension');control.commit()
                require(not control.in_transaction and target.in_transaction,'journal_control_commit_unknown')
            except BaseException:
                if control.in_transaction:control.rollback()
                raise
    return dict(installed=True,migration_id=MIGRATION)

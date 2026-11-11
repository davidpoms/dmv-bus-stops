"""Full-owner interruption and restart probes; no real production resources."""
import json
from pathlib import Path
import shutil
import sys
import unittest
from uuid import uuid4
from tests.runtime_deadline_harness import run_child


class OwnerFailureTests(unittest.TestCase):
    observations={}

    def run_case(self,scenario):
        if scenario in self.observations:return self.observations[scenario]
        root=Path(__file__).resolve().parents[1]
        evidence=root/'.tmp'/('r28-fault-'+uuid4().hex+'.json')
        def cleanup():
            if evidence.exists():
                name=json.loads(evidence.read_text()).get('root')
                if name:
                    workspace=Path(name).resolve()
                    self.assertEqual(root,workspace.parent)
                    self.assertTrue(workspace.name.startswith('recognition-owner-r28-'))
                    if workspace.exists():shutil.rmtree(workspace)
                evidence.unlink(missing_ok=True)
        self.addCleanup(cleanup)
        first=run_child([sys.executable,'-B','-m','tests.runtime_owner_fault_probe',scenario,str(evidence)],timeout=540)
        self.assertEqual('child_exited',first['status'],first)
        self.assertTrue(first['reaped'] and first['cleanup_complete'] and not first['parent_bound_exceeded'])
        self.assertEqual(dict(before_commit=91,after_commit=92,restart=93).get(scenario,0),first['exit_code'])
        self.assertTrue(evidence.is_file(),'no owner checkpoint; preparation failed')
        workspace=Path(json.loads(evidence.read_text())['root']).resolve()
        self.assertEqual(root,workspace.parent);self.assertTrue(workspace.name.startswith('recognition-owner-r28-'))
        try:
            inspection=run_child([sys.executable,'-B','-m','tests.runtime_owner_fault_probe','inspect',str(evidence)],timeout=90)
            self.assertEqual('child_exited',inspection['status'],inspection)
            self.assertEqual(0,inspection['exit_code'],inspection)
            self.assertTrue(inspection['reaped'] and inspection['cleanup_complete'] and not inspection['parent_bound_exceeded'])
            report=inspection['reports'][-1]
            expected=0 if scenario in ('before_commit','restart','revoked','concurrent') else 1
            self.assertEqual(expected,report['effects']);self.assertEqual(expected,report['witnesses'])
            self.assertFalse(report['retry_authorized']);self.assertTrue(report['fresh_authentication'])
            self.assertTrue(report['old_handoff_rejected'])
            record=dict(scenario=scenario,child_seconds=first['elapsed_seconds'],inspection_seconds=inspection['elapsed_seconds'],**report)
            record['concurrent_rejected']=bool(first['reports'] and first['reports'][-1].get('concurrent_rejected'))
            self.observations[scenario]=record
            artifact=root/'.tmp'/'recognition-r28-owner-fault-results.json'
            artifact.write_text(json.dumps(self.observations,indent=2)+'\n')
            print('R28_OWNER_FAILURE '+json.dumps(record))
            return record
        finally:
            # Only this child-reported, verified fresh fixture directory.
            self.assertEqual(root,workspace.parent)
            shutil.rmtree(workspace)
            evidence.unlink(missing_ok=True)

    def test_crash_before_target_commit(self):self.run_case('before_commit')
    def test_crash_after_target_commit(self):self.run_case('after_commit')
    def test_lost_response_after_target_commit(self):
        # The abrupt postcommit child exit publishes no result; fresh inspection
        # of that SAME durable state proves no new execution right.
        self.assertEqual(1,self.run_case('after_commit')['effects'])
    def test_control_recording_failure(self):self.run_case('control_failure')
    def test_restart_after_pending(self):self.assertTrue(self.run_case('before_commit')['old_handoff_rejected'])
    def test_duplicate_recovery_remains_inspection(self):self.assertFalse(self.run_case('after_commit')['retry_authorized'])
    def test_concurrent_original_owner_binding(self):self.assertTrue(self.run_case('concurrent')['concurrent_rejected'])
    def test_revoked_owner_authority(self):self.run_case('revoked')

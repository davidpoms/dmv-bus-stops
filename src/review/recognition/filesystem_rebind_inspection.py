"""Read-only, advisory inspection for the existing v2 device-only ceremony."""

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import re
import sqlite3

from . import administration as a
from .rules import digest
from .trust import load


def _utc_now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _error(error):
    code = getattr(error, 'code', None)
    return code if isinstance(code, str) and re.fullmatch('[a-z0-9_]{1,120}', code) else type(error).__name__


def _identity(value):
    keys = ('hostname', 'database', 'device', 'inode')
    return {k: value.get(k) for k in keys} if isinstance(value, dict) else None


def _target_metadata(target, owner_id):
    rows = [dict(row) for row in target.execute(
        'SELECT installation_id,target_id,owner_id FROM recognition_local_installation')]
    owner = target.execute('SELECT role,email_verified_at FROM community_reviewers WHERE id=?', (owner_id,)).fetchone()
    return dict(installations=rows, owner=dict(exists=owner is not None,
        role=owner['role'] if owner else None, verified=bool(owner and owner['email_verified_at'])))


def inspect_rebind(target_path, control_path, *, expected_generation):
    """No key, write connection, audit append, reservation or rebind invocation.

    Passing checks are observations, not an authorization or a promise that a
    later writer reservation will succeed. Never substitutes for ceremony checks.
    """
    result = dict(classification='NOT_ELIGIBLE_FOR_REBIND', advisory_only=True,
        rebind_authorized=False, write_reservation_acquired=False,
        observation_context='calling_process_not_necessarily_wsgi',
        expected_generation=expected_generation, current_generation=None,
        binding_history_valid=False, audit_history_valid=False, history_valid=False,
        binding_format=None, binding_sha256=None, installation_id=None, target_id=None, owner_id=None,
        recorded_control_identity=None, observed_control_identity=None,
        recorded_target_identity=None, observed_target_identity=None,
        recorded_target_schema_sha256=None, observed_target_schema_sha256=None,
        owner_status=None, target_installation=None, target_sha256=None,
        only_devices_differ=False, prerequisites_all_pass=False, checks={}, failed_conditions=[])

    def check(name, condition, code, **details):
        passed = bool(condition)
        result['checks'][name] = passed
        if not passed:
            result['failed_conditions'].append(dict(condition=name, code=code, **details))
        return passed

    def read(name, operation):
        try:
            value = operation()
        except (ValueError, OSError, sqlite3.Error, KeyError, TypeError, IndexError) as error:
            check(name, False, _error(error))
            return None
        result['checks'][name] = True
        return value

    def paths():
        a.need(isinstance(target_path, Path) and isinstance(control_path, Path)
               and target_path.is_absolute() and control_path.is_absolute(), 'explicit_admin_paths_required', 503)
        a.need(target_path.resolve() != control_path.resolve(), 'separate_control_store_required', 503)
        return target_path, control_path

    if read('paths_valid', paths) is None:
        return result
    result.update(configured_control_path=str(control_path), configured_target_path=str(target_path))
    check('expected_generation_valid', type(expected_generation) is int and expected_generation >= 1,
          'filesystem_rebind_generation_conflict')
    try:
        with a.connect(control_path) as control, a.connect(target_path) as target:
            control.execute('BEGIN')
            target.execute('BEGIN')
            read('control_schema_valid', lambda: a.schema.check_control(control))
            head = read('audit_history_valid', lambda: a._audit_head(control))
            result['audit_history_valid'] = result['checks']['audit_history_valid']
            binding = None
            try:
                binding = a._binding(control)
                result['checks']['binding_history_valid'] = True
            except a.AdminError as error:
                if error.code == 'runtime_profile_contract_not_enabled':
                    # _binding validates the entire chain before its v3 gate.
                    result['checks']['binding_history_valid'] = True
                    binding = load(control.execute('SELECT body_json FROM recognition_admin_bindings '
                                                   'ORDER BY generation DESC LIMIT 1').fetchone()[0])
                else:
                    check('binding_history_valid', False, error.code)
            result['binding_history_valid'] = result['checks'].get('binding_history_valid', False)
            result['history_valid'] = all(result['checks'].get(k, False) for k in (
                'control_schema_valid', 'binding_history_valid', 'audit_history_valid'))
            if binding is None:
                # Show only recorded metadata; never replace invalid history with
                # current observations or use this row to admit the ceremony.
                row = control.execute('SELECT body_json FROM recognition_admin_bindings '
                                      'ORDER BY generation DESC LIMIT 1').fetchone()
                binding = load(row[0]) if row else {}
            a.need(type(binding) is dict, 'installation_history_integrity_failure', 503)
            result.update(current_generation=binding.get('generation'), binding_format=binding.get('format'),
                binding_sha256=digest(binding), installation_id=binding.get('installation_id'),
                target_id=binding.get('target_id'), owner_id=binding.get('owner_id'),
                recorded_control_identity=_identity(binding.get('control_identity')),
                recorded_target_identity=_identity(binding.get('target', {}).get('observation')),
                recorded_target_schema_sha256=binding.get('target', {}).get('schema_sha256'))
            check('binding_is_v2', binding.get('format') == 'recognition-local-control-v2', 'v2_binding_required')
            check('generation_matches', type(expected_generation) is int
                  and type(binding.get('generation')) is int and expected_generation == binding['generation'],
                  'filesystem_rebind_generation_conflict')
            check('clock_valid', head is None or a.timestamp(_utc_now()) >= a.timestamp(load(head['body_json'])['at_utc']),
                  'admin_clock_or_audit_failure')
            observed_control = read('control_observation_valid', lambda: asdict(a.target_identity(control)))
            observed_target = read('target_observation_valid', lambda: a.observe_target(target))
            result['observed_control_identity'] = observed_control
            if observed_target:
                result.update(observed_target_identity=observed_target['observation'],
                              observed_target_schema_sha256=observed_target['schema_sha256'],
                              target_sha256=digest(observed_target))
            expected_fields = {'hostname', 'database', 'device', 'inode'}
            differences = {}
            for name, recorded, observed in (
                    ('control', binding.get('control_identity'), observed_control),
                    ('target', binding.get('target', {}).get('observation'),
                     observed_target['observation'] if observed_target else None)):
                shape = (type(recorded) is dict and type(observed) is dict
                         and set(recorded) == set(observed) == expected_fields)
                check(name+'_identity_fields_valid', shape, 'filesystem_rebind_non_device_mismatch')
                changed = sorted(k for k in expected_fields if shape and recorded[k] != observed[k])
                differences[name] = changed if shape else None
                check(name+'_non_device_fields_match', shape and not (set(changed)-{'device'}),
                      'filesystem_rebind_non_device_mismatch', differing_fields=changed if shape else None)
            result['identity_differences'] = differences
            check('configured_paths_match', str(control_path) == binding.get('control_identity', {}).get('database')
                  and str(target_path) == binding.get('target', {}).get('observation', {}).get('database'),
                  'filesystem_rebind_path_mismatch')
            drift = any(value is not None and 'device' in value for value in differences.values())
            check('device_drift_present', drift, 'filesystem_rebind_device_unchanged')
            result['only_devices_differ'] = drift and all(value is not None and not (set(value)-{'device'})
                                                         for value in differences.values())
            check('target_schema_matches', observed_target is not None
                  and observed_target['schema_sha256'] == result['recorded_target_schema_sha256'],
                  'filesystem_rebind_schema_mismatch')
            read('target_installation_schema_valid', lambda: a.schema.check_target(target))
            metadata = read('target_metadata_readable', lambda: _target_metadata(target, binding.get('owner_id')))
            if metadata is not None:
                result.update(owner_status=metadata['owner'], target_installation=metadata['installations'])
                # Match the existing ceremony's first-row predicate; the target
                # singleton schema is independently verified above.
                row = metadata['installations'][0] if metadata['installations'] else None
                check('logical_ids_match', row is not None and all(row[k] == binding.get(k)
                      for k in ('installation_id', 'target_id', 'owner_id')), 'installation_target_mismatch')
                check('owner_verified', metadata['owner']['role'] == 'owner' and metadata['owner']['verified'],
                      'verified_project_owner_required')
            # No claim of a cross-database atomic snapshot. Detect observed
            # changes with new read-only snapshots; later rebind must recheck.
            with a.connect(control_path) as fresh_control, a.connect(target_path) as fresh_target:
                fresh_control.execute('BEGIN')
                fresh_target.execute('BEGIN')
                a.schema.check_control(fresh_control)
                fresh_row = fresh_control.execute('SELECT generation,body_json,body_sha256 FROM '
                    'recognition_admin_bindings ORDER BY generation DESC LIMIT 1').fetchone()
                initial_row = control.execute('SELECT generation,body_json,body_sha256 FROM '
                    'recognition_admin_bindings ORDER BY generation DESC LIMIT 1').fetchone()
                fresh_head = a._audit_head(fresh_control)
                check('observations_stable', fresh_row is not None
                    and initial_row is not None and tuple(fresh_row) == tuple(initial_row)
                    and (tuple(fresh_head) if fresh_head else None) == (tuple(head) if head else None)
                    and asdict(a.target_identity(fresh_control)) == observed_control
                    and a.observe_target(fresh_target) == observed_target
                    and _target_metadata(fresh_target, binding.get('owner_id')) == metadata,
                    'filesystem_rebind_observation_changed')
    except (ValueError, OSError, sqlite3.Error, KeyError, TypeError, IndexError, AttributeError) as error:
        check('inspection_completed', False, _error(error))
    result['prerequisites_all_pass'] = bool(result['checks']) and all(result['checks'].values())
    if result['prerequisites_all_pass']:
        result['classification'] = 'ELIGIBLE_FOR_REBIND'
    return result

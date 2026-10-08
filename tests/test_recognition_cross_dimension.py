"""Synthetic in-memory packages only: no application or audit database access."""
from copy import deepcopy
from unittest.mock import patch

import pytest

from src.review.recognition.cross_dimension import build_cross_dimension_report

FORMATS = {"dc_ward": "dc-ward-evidence-package-v1", "dc_anc": "dc_anc_private_evidence_v1",
           "county": "county_private_evidence_v1", "state": "state_private_evidence_v1",
           "census_place": "Census_place_private_evidence_v1"}
from src.review.recognition.rules import digest


def seal(packages):
    for dim, envelope in packages.items():
        b = envelope['evidence_package']
        for s in b['scope_records']:
            s['membership_sha256'] = digest(s['membership'])
            key = 'metadata_sha256' if dim in ('state', 'census_place') else 'scope_metadata_sha256'
            s[key] = digest(s['metadata'])
            if 'coordinate_discovery_members' in s:
                s['coordinate_discovery_members_sha256'] = digest(s['coordinate_discovery_members'])
        envelope['evidence_package_sha256'] = digest(b)
    packages['census_place']['evidence_package']['state_evidence_reference'] = {
        'package_sha256': packages['state']['evidence_package_sha256']}
    state_rows = {r['physical_stop_id']: r for r in packages['state']['evidence_package'].get('active_stop_evidence', [])}
    for r in packages['census_place']['evidence_package'].get('active_stop_evidence', []):
        r['state_cross_source_evidence'] = deepcopy(state_rows.get(r['physical_stop_id']))
    packages['census_place']['evidence_package_sha256'] = digest(packages['census_place']['evidence_package'])
    return packages


def fixture():
    packages = {}
    rows = [{'physical_stop_id': i, 'current_gtfs': 1} for i in (1, 2, 3)]
    events = [{'id': 9, 'event_type': 'replacement'}]
    edges = [{'event_id': 9, 'predecessor_physical_stop_id': 1, 'successor_physical_stop_id': 2}]
    states = [{'physical_stop_id': i, 'identity_status': 'manual_exception' if i == 3 else 'current'} for i in (1, 2, 3)]
    for dim, fmt in FORMATS.items():
        meta = {'scope_key': dim + ':source', 'certification_status': 'pending_independent_review',
                'certification_reference': None, 'scope_version': None, 'state': 'DC'}
        if dim == 'dc_anc':
            meta['source_identity'] = {'ANC_ID': '3/4G'}
        if dim == 'county':
            meta['classification'] = 'independent_city_county_equivalent'
        if dim == 'census_place':
            meta['classification'] = 'CDP'
        scope = {'metadata': meta, 'membership': deepcopy(rows[:2])}
        if dim == 'state':
            scope['membership'] = deepcopy(rows)
        if dim == 'dc_ward':
            scope['coordinate_discovery_members'] = [1]  # Distinct evidence, not replacement membership.
        b = {'format': fmt, 'scope_records': [scope], 'quality_checks': {},
             'original_jurisdiction_rows': [{'stop_id': i, 'state': 'DC'} for i in (1, 2, 3)]}
        snap = {'sha256': 'a' * 64}
        if dim in ('dc_ward', 'dc_anc'):
            b['source_snapshot'] = snap
        else:
            b['snapshot'] = snap
        key = {'dc_ward': 'source_gtfs_status_rows', 'state': 'source_gtfs_rows'}.get(dim, 'gtfs_status_rows')
        b[key] = deepcopy(rows)
        if dim == 'dc_ward':
            b['original_stop_jurisdiction_rows'] = b.pop('original_jurisdiction_rows')
            b['identity_history'] = {'all_events': events, 'all_edges': edges, 'represented_member_states': states}
        else:
            b['identity_history'] = {'events': events, 'edges': edges, 'states': states}
        packages[dim] = {'evidence_package': deepcopy(b)}
    packages['county']['evidence_package']['quality_checks'] = {'state_boundary_mismatch': [1, 2], 'ambiguous_label_crosswalk': [2]}
    packages['census_place']['evidence_package']['quality_checks'] = {'state_context_conflict': [2], 'label_mismatch': [2]}
    county_identity = {'STATEFP': '51', 'GEOID': '51510', 'NAME': 'Alexandria',
                       'NAMELSAD': 'Alexandria city', 'CLASSFP': 'C7', 'LSAD': '25'}
    place_identity = {'STATEFP': '51', 'GEOID': '5103000', 'NAME': 'Arlington',
                      'NAMELSAD': 'Arlington CDP', 'CLASSFP': 'U1', 'LSAD': '57'}
    county = packages['county']['evidence_package']
    place = packages['census_place']['evidence_package']
    county['scope_records'][0]['metadata'].update(source_identity=county_identity, state='VA',
        boundary_artifact='data/geography/md_va_counties.geojson', boundary_sha256='b' * 64)
    place['scope_records'][0]['metadata'].update(source_identity=place_identity, state='VA',
        source_artifact='data/geography/va_places.geojson', source_sha256='c' * 64)
    county['boundary'] = {'all_source_feature_properties': [county_identity],
                         'path': 'data/geography/md_va_counties.geojson', 'sha256': 'b' * 64}
    place['sources'] = {'va_places': {'all_feature_properties': [place_identity], 'sha256': 'c' * 64}}
    packages['state']['evidence_package']['sources'] = {'va_places': {'sha256': 'c' * 64}}
    packages['dc_ward']['evidence_package']['identity_history']['represented_member_states'] = deepcopy(states[:2])
    for dim, env in packages.items():
        b = env['evidence_package']
        if dim != 'dc_ward':
            b['active_stop_evidence'] = [{'physical_stop_id': i} for i in (1, 2, 3)]
        else:
            b['active_stop_original_evidence'] = [{'physical_stop_id': i} for i in (1, 2, 3)]
        if dim not in ('dc_ward', 'dc_anc'):
            b['snapshot']['manifest'] = {'backup_sha256': 'A' * 64}
    for r in packages['dc_anc']['evidence_package']['active_stop_evidence']:
        r['polygon_matches'] = ['3/4G'] if r['physical_stop_id'] < 3 else []
    for r in county['active_stop_evidence']:
        r['coordinate_matches'] = ['51510'] if r['physical_stop_id'] < 3 else []
    for r in packages['state']['evidence_package']['active_stop_evidence']:
        r['pipeline_result'] = {'state': 'DC'}
    for r in place['active_stop_evidence']:
        r['coordinate_place_geoids'] = ['5103000'] if r['physical_stop_id'] < 3 else []
    for dim, label in [('county', 'Alexandria'), ('census_place', 'Arlington')]:
        for r in packages[dim]['evidence_package']['original_jurisdiction_rows']:
            r['county' if dim == 'county' else 'municipality'] = label if r['stop_id'] < 3 else None
    return seal(packages)


def test_deterministic_pure_and_preserves_inputs():
    p = fixture()
    original = deepcopy(p)
    with patch('builtins.open', side_effect=AssertionError('no files')), patch('sqlite3.connect', side_effect=AssertionError('no database')):
        a = build_cross_dimension_report(p)
        b = build_cross_dimension_report(dict(reversed(list(p.items()))))
    assert a == b and p == original
    assert a['status'] == 'pending_adjudication'
    assert a['report_sha256'] == digest({k: v for k, v in a.items() if k != 'report_sha256'})
    assert a['issuance_ready'] is False
    assert a['active_stop_denominator'] == 3


def test_adapters_preserve_distinctions_and_membership_basis():
    r = build_cross_dimension_report(fixture())
    stop = r['stop_records'][1]
    assert stop['dimensions']['dc_ward']['supplied_memberships']  # Coordinate discovery omitted 2.
    assert stop['dimensions']['dc_anc']['supplied_memberships'][0]['metadata']['source_identity']['ANC_ID'] == '3/4G'
    assert stop['dimensions']['county']['supplied_memberships'][0]['metadata']['classification'] == 'independent_city_county_equivalent'
    assert stop['dimensions']['census_place']['supplied_memberships'][0]['metadata']['classification'] == 'CDP'
    assert r['stop_records'][2]['dimensions']['state']['identity_history']['manual_exception']
    assert not r['stop_records'][2]['dimensions']['census_place']['supplied_memberships']


def test_intersections_and_missing_coverage():
    r = build_cross_dimension_report(fixture())
    pair = next(x for x in r['intersections'] if x['left'] == 'census_place:state_boundary_conflict' and x['right'] == 'county:state_boundary_conflict')
    assert pair['physical_stop_ids'] == [1, 2] and pair['count'] == 2
    assert r['dimension_counts']['census_place'] == {'represented': 2, 'missing': 1}
    assert r['affected_stop_indexes']['state:manual_exception']['physical_stop_ids'] == [3]


@pytest.mark.parametrize('kind', ['payload', 'metadata', 'membership', 'coordinate'])
def test_bad_hash_quarantines_everything(kind):
    p = fixture()
    b = p['dc_ward']['evidence_package']
    if kind == 'payload':
        b['purpose'] = 'changed'
    else:
        key = {'metadata': 'scope_metadata_sha256', 'membership': 'membership_sha256', 'coordinate': 'coordinate_discovery_members_sha256'}[kind]
        b['scope_records'][0][key] = '0' * 64
        p['dc_ward']['evidence_package_sha256'] = digest(b)
    r = build_cross_dimension_report(p)
    assert r['status'] == 'quarantined' and r['stop_records'] == [] and r['issuance_ready'] is False


@pytest.mark.parametrize('kind', ['snapshot', 'denominator', 'duplicate', 'bool', 'inactive', 'format', 'identity', 'state_reference'])
def test_invalid_resealed_inputs_quarantined(kind):
    p = fixture()
    b = p['county']['evidence_package']
    if kind == 'snapshot': b['snapshot']['sha256'] = 'b' * 64
    if kind == 'denominator': b['gtfs_status_rows'].append({'physical_stop_id': 4, 'current_gtfs': 1})
    if kind == 'duplicate': b['scope_records'].append(deepcopy(b['scope_records'][0]))
    if kind == 'bool': b['scope_records'][0]['membership'][0]['current_gtfs'] = True
    if kind == 'inactive': b['scope_records'][0]['membership'][0]['physical_stop_id'] = 99
    if kind == 'format': b['format'] = 'future-format'
    if kind == 'identity': b['identity_history']['edges'] = []
    seal(p)
    if kind == 'state_reference':
        b = p['census_place']['evidence_package']
        b['state_evidence_reference']['package_sha256'] = '0' * 64
        p['census_place']['evidence_package_sha256'] = digest(b)
    assert build_cross_dimension_report(p)['status'] == 'quarantined'


def test_no_promotion_and_malformed_inputs():
    p = fixture()
    p['state']['evidence_package']['scope_records'][0]['metadata']['certification_status'] = 'approved'
    seal(p)
    assert build_cross_dimension_report(p)['status'] == 'quarantined'
    for bad in (None, {}, {'dc_ward': []}):
        assert build_cross_dimension_report(bad)['status'] == 'quarantined'


def test_scope_order_and_overlap_are_not_silent_selection():
    p = fixture()
    b = p['census_place']['evidence_package']
    second = deepcopy(b['scope_records'][0])
    second['metadata']['scope_key'] = 'census_place:other'
    b['scope_records'].append(second)
    seal(p)
    first = build_cross_dimension_report(p)
    assert len(first['stop_records'][0]['dimensions']['census_place']['supplied_memberships']) == 2
    # Reordering mapping keys does not change hashes or report bytes.
    assert first == build_cross_dimension_report(dict(reversed(list(p.items()))))


def index(report, name):
    return report['affected_stop_indexes'].get(name, {'physical_stop_ids': []})['physical_stop_ids']


def test_quality_indexes_are_not_authoritative():
    p = fixture()
    for env in p.values():
        env['evidence_package']['quality_checks'] = {'invented': [999999]}
    seal(p)
    r = build_cross_dimension_report(p)
    assert index(r, 'county:state_boundary_conflict') == [1, 2]
    # Change the actual State membership assertion, without changing quality indexes.
    p['state']['evidence_package']['scope_records'][0]['metadata']['state'] = 'VA'
    seal(p)
    r = build_cross_dimension_report(p)
    assert index(r, 'county:state_boundary_conflict') == []
    assert index(r, 'state:coordinate_vs_stored_disagreement') == [1, 2, 3]


def test_stored_labels_and_nulls_are_compared_to_discovery():
    p = fixture()
    labels = p['census_place']['evidence_package']['original_jurisdiction_rows']
    labels[0]['municipality'] = 'District of Columbia'
    labels[1]['municipality'] = None
    labels[2]['municipality'] = 'District of Columbia'
    seal(p)
    r = build_cross_dimension_report(p)
    assert index(r, 'census_place:source_label_disagreement') == [1]
    assert index(r, 'census_place:null_label_with_coordinate_membership') == [2]
    assert index(r, 'census_place:stored_label_without_coordinate_membership') == [3]
    d = r['stop_records'][0]['dimensions']['census_place']
    assert d['assessment'] == 'disagreement' and d['comparable_assertions_used']
    assert d['separately_reported_discoveries']['coordinate_place_geoids'] == ['5103000']
    assert d['classification_notices'][0]['code'] == 'CDP_not_incorporated_place'


def test_global_and_context_crosswalks_and_overlaps():
    p = fixture()
    place = p['census_place']['evidence_package']
    cat = place['sources']['va_places']['all_feature_properties']
    extra = deepcopy(cat[0]);extra.update(GEOID='2400010', STATEFP='24')
    cat.append(extra)
    for r in place['original_jurisdiction_rows']: r['state'] = 'VA'
    seal(p)
    r = build_cross_dimension_report(p)
    assert index(r, 'census_place:ambiguous_global_crosswalk') == [1, 2]
    assert not index(r, 'census_place:ambiguous_state_context_crosswalk')
    extra = deepcopy(cat[0]);extra['GEOID'] = '5100001';cat.append(extra)
    seal(p)
    r = build_cross_dimension_report(p)
    assert index(r, 'census_place:ambiguous_state_context_crosswalk') == [1, 2]
    pair = next(x for x in r['intersections'] if x['left'] == 'census_place:ambiguous_global_crosswalk'
                and x['right'] == 'census_place:ambiguous_state_context_crosswalk')
    assert pair['count'] == 2


@pytest.mark.parametrize('mutation,code', [
    ('source', 'source_artifact_hash_disagreement'),
    ('manifest', 'embedded_snapshot_mismatch'),
    ('embedded', 'embedded_state_content_mismatch'),
    ('edge_event', 'unknown_edge_event'),
])
def test_provenance_and_identity_validation(mutation, code):
    p = fixture()
    if mutation == 'source':
        p['state']['evidence_package']['sources']['va_places']['sha256'] = 'd' * 64
    if mutation == 'manifest':
        p['county']['evidence_package']['snapshot']['manifest']['backup_sha256'] = 'b' * 64
    if mutation == 'edge_event':
        for env in p.values():
            h = env['evidence_package']['identity_history']
            h.get('edges', h.get('all_edges'))[0]['event_id'] = 999
    seal(p)
    if mutation == 'embedded':
        b = p['census_place']['evidence_package']
        b['active_stop_evidence'][0]['state_cross_source_evidence']['pipeline_result']['state'] = 'MD'
        p['census_place']['evidence_package_sha256'] = digest(b)
    r = build_cross_dimension_report(p)
    assert r['status'] == 'quarantined' and r['errors'] == [code]
    assert r['validation_details']['code'] == code and r['stop_records'] == []


def test_identity_missing_is_unknown_not_false():
    p = fixture()
    for dim in ('dc_anc', 'county', 'state', 'census_place'):
        h = p[dim]['evidence_package']['identity_history']
        h['states'] = [s for s in h['states'] if s['physical_stop_id'] != 3]
    seal(p)
    r = build_cross_dimension_report(p)
    d = r['stop_records'][2]['dimensions']['state']
    assert d['identity_history']['manual_exception'] is None
    assert d['identity_history']['status'] == 'unknown'
    assert index(r, 'state:identity_evidence_incomplete') == [3]


def test_retired_predecessor_not_required_to_be_active_and_orphan_event_flagged():
    p = fixture()
    for dim, env in p.items():
        h = env['evidence_package']['identity_history']
        h.get('events', h.get('all_events')).append({'id': 10, 'event_type': 'creation'})
        h.get('edges', h.get('all_edges'))[0]['predecessor_physical_stop_id'] = 99
        if dim != 'dc_ward':
            h['states'].append({'physical_stop_id': 99, 'identity_status': 'retired', 'retirement_event_id': 9})
    seal(p)
    r = build_cross_dimension_report(p)
    assert r['status'] == 'pending_adjudication'
    assert any(x['code'] == 'events_without_attributable_edges' for x in r['identity_history_findings'])
    assert not any(x['code'] == 'edge_identity_evidence_missing' for x in r['identity_history_findings'])


def test_order_changes_preserve_interpretation_but_input_hashes_change():
    p = fixture()
    scope = deepcopy(p['county']['evidence_package']['scope_records'][0])
    scope['metadata']['scope_key'] = 'county:second'
    scope['membership'] = []
    p['county']['evidence_package']['scope_records'].append(scope)
    seal(p)
    first = build_cross_dimension_report(p)
    for env in p.values():
        b = env['evidence_package']; b['scope_records'].reverse()
        for s in b['scope_records']: s['membership'].reverse()
    seal(p)
    second = build_cross_dimension_report(p)
    assert first['dimension_counts'] == second['dimension_counts']
    assert first['affected_stop_indexes'] == second['affected_stop_indexes']
    assert first['intersections'] == second['intersections']
    # Supplied canonical JSON hashes intentionally bind list order.
    assert first['input_package_hashes'] != second['input_package_hashes']
    assert second == build_cross_dimension_report(p)


def test_purity_blocks_files_database_and_network():
    p = fixture()
    with patch('builtins.open', side_effect=AssertionError('file')), \
         patch('pathlib.Path.open', side_effect=AssertionError('path')), \
         patch('sqlite3.connect', side_effect=AssertionError('database')), \
         patch('socket.socket', side_effect=AssertionError('network')), \
         patch('socket.create_connection', side_effect=AssertionError('network')), \
         patch('urllib.request.urlopen', side_effect=AssertionError('network')):
        for inputs in (p, {}):
            r = build_cross_dimension_report(inputs)
            assert r['issuance_ready'] is False
            assert r['certification_action'] == 'none'
            assert r['purpose'] == 'evidence_adjudication_only'


@pytest.mark.parametrize('overlap', [57, 19, 6, 1, 53, 27, 531, 233, 7])
def test_scaled_intersections_are_computed_from_ids(overlap):
    p = fixture()
    count = overlap + 2
    rows = [{'physical_stop_id': i, 'current_gtfs': 1} for i in range(1, count + 1)]
    for dim, env in p.items():
        b = env['evidence_package']
        key = {'dc_ward': 'source_gtfs_status_rows', 'state': 'source_gtfs_rows'}.get(dim, 'gtfs_status_rows')
        b[key] = deepcopy(rows)
        b['scope_records'][0]['membership'] = deepcopy(rows if dim == 'state' else rows[:overlap])
        labelkey = 'original_stop_jurisdiction_rows' if dim == 'dc_ward' else 'original_jurisdiction_rows'
        b[labelkey] = [{'stop_id': i, 'state': 'DC'} for i in range(1, count + 1)]
        h = b['identity_history']
        h['represented_member_states' if dim == 'dc_ward' else 'states'] = [
            {'physical_stop_id': i, 'identity_status': 'current'} for i in range(1, count + 1)]
    seal(p)
    r = build_cross_dimension_report(p)
    pair = next(x for x in r['intersections'] if x['left'] == 'census_place:state_boundary_conflict'
                and x['right'] == 'county:state_boundary_conflict')
    assert pair['physical_stop_ids'] == list(range(1, overlap + 1))
    assert pair['count'] == overlap


def test_determinism_across_process_hash_seeds():
    import os
    import subprocess
    import sys
    code = ("import runpy; t=runpy.run_path('tests/test_recognition_cross_dimension.py'); "
            "print(t['build_cross_dimension_report'](t['fixture']())['report_sha256'])")
    results = []
    for seed in ('1', '777'):
        env = dict(os.environ, PYTHONHASHSEED=seed, PYTHONDONTWRITEBYTECODE='1')
        results.append(subprocess.check_output([sys.executable, '-B', '-c', code], env=env, text=True).strip())
    assert results[0] == results[1]


def test_independent_city_place_identity_disagreement():
    p = fixture()
    b = p['census_place']['evidence_package']
    m = b['scope_records'][0]['metadata']
    m['classification'] = 'independent_city'
    m['source_identity'].update(CLASSFP='C7', NAME='Falls Church', NAMELSAD='Falls Church city')
    seal(p)
    r = build_cross_dimension_report(p)
    assert index(r, 'census_place:county_place_identity_disagreement') == [1, 2]
    assert index(r, 'census_place:independent_city_county_equivalent') == [1, 2]


def test_ward_subset_unknown_does_not_override_other_identity_evidence():
    p = fixture()
    h = p['dc_ward']['evidence_package']['identity_history']
    assert all(r['physical_stop_id'] != 3 for r in h['represented_member_states'])
    seal(p)
    r = build_cross_dimension_report(p)
    assert r['stop_records'][2]['dimensions']['state']['identity_history']['manual_exception'] is True
    assert r['stop_records'][2]['dimensions']['dc_ward']['identity_history']['manual_exception'] is None


def test_identity_edge_and_manual_sets_intersect_without_double_counting():
    p = fixture()
    for dim, env in p.items():
        h = env['evidence_package']['identity_history']
        for row in h.get('states', h.get('represented_member_states')):
            if row['physical_stop_id'] == 2: row['identity_status'] = 'manual_exception'
    seal(p)
    r = build_cross_dimension_report(p)
    assert index(r, 'state:manual_exception') == [2, 3]
    assert index(r, 'state:identity_edge_involvement') == [1, 2]
    pair = next(x for x in r['intersections'] if x['left'] == 'state:identity_edge_involvement'
                and x['right'] == 'state:manual_exception')
    assert pair['physical_stop_ids'] == [2]

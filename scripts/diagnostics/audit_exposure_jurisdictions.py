"""Read-only jurisdiction coverage and comparison audit on an explicit DB copy."""
import argparse
from contextlib import closing
import csv
import json
from pathlib import Path
import sqlite3
import time

from src.scoring.exposure_map import exposure_rows, geography_options, compare_rows, weekday_divisor


def audit(path):
    with closing(sqlite3.connect(f"file:{Path(path).resolve().as_posix()}?mode=ro", uri=True)) as conn:
        start = time.perf_counter()
        rows = exposure_rows(conn)
        elapsed = time.perf_counter() - start
        groups = geography_options(rows)
        brief = lambda r: {k: r.get(k) for k in ('physical_stop_id','stop_name','exposure_score',
            'ridership_value','regional_band','jurisdiction_band','jurisdiction_rank','bench_status')}
        top = {'DMV': [brief(r) for r in rows[:10]]}
        examples, small = [], []
        coverage = {}
        for dimension in groups:
            kind = dimension['type']
            coverage[kind] = dict(assigned=sum(v['population'] for v in dimension['values']),
                                  missing=len(rows)-sum(v['population'] for v in dimension['values']),
                                  groups=dimension['values'])
            for group in dimension['values']:
                compared, context = compare_rows(rows, kind, group['value'])
                if context['small_population']:
                    small.append(context)
                if kind in ('state','county'):
                    top[f"{kind}: {group['value']}"] = [brief(r) for r in compared[:10]]
                    changed = [r for r in compared if r['jurisdiction_band']=='Very High'
                               and r['regional_band'] in ('Lower','Moderate','High')]
                    changed.sort(key=lambda r: (r['regional_percentile'], r['physical_stop_id']))
                    if changed:
                        examples.append(dict(geography_type=kind, geography_value=group['value'],
                                             population=context['population'], stop=brief(changed[0])))
        period = conn.execute('SELECT MAX(period) FROM ridership_snapshots').fetchone()[0]
        snapshot_rows = conn.execute('SELECT route_id,weekday_boardings,monthly_boardings,saturday_boardings,sunday_boardings FROM ridership_snapshots WHERE period=?',(period,)).fetchall()
        csv_path = Path(__file__).resolve().parents[2] / 'data/raw/ridership/wmata_ridership.csv'
        with csv_path.open(encoding='utf-8-sig') as source:
            exported = {r['Route']: float(r['Weekday'].replace(',','')) for r in csv.DictReader(source, delimiter='\t')}
        return dict(source_period=period, weekday_divisor=weekday_divisor(period),
                    source_unit='Monthly weekday boarding total; calendar-weekday estimate only',
                    snapshot_rows=len(snapshot_rows), csv_value_matches=sum(exported.get(r[0])==r[1] for r in snapshot_rows),
                    monthly_sum_matches=sum(abs(r[2]-r[1]-r[3]-r[4])<=1 for r in snapshot_rows),
                    active=len(rows), usable=sum(r['exposure_score'] is not None for r in rows),
                    coverage=coverage, top_10=top, regional_local_examples=examples,
                    small_groups=small, derivation_seconds=round(elapsed,4),
                    dc_with_county=sum(r['geographies'].get('state')=='DC' and bool(r['geographies'].get('county')) for r in rows),
                    integrity_check=conn.execute('PRAGMA integrity_check').fetchone()[0],
                    foreign_key_violations=len(conn.execute('PRAGMA foreign_key_check').fetchall()))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(audit(args.db), indent=2) + '\n', encoding='utf-8')

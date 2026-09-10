"""Read-only exposure audit. Run as a module with --db pointing to a fresh copy."""
import argparse
from collections import Counter
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import time

from src.scoring.exposure_map import exposure_rows, map_payload


def audit(path):
    with closing(sqlite3.connect(f"file:{Path(path).resolve().as_posix()}?mode=ro", uri=True)) as conn:
        started = time.perf_counter()
        rows = exposure_rows(conn)
        elapsed = time.perf_counter() - started
        top = rows[:20]
        connections = sorted(rows, key=lambda r: (-r['active_route_count'], r['physical_stop_id']))[:20]
        def brief(row):
            return {key: row[key] for key in ('physical_stop_id', 'stop_name', 'exposure_score',
                    'exposure_band', 'active_route_count', 'bench_status')}
        # Independently reconcile the materialized score with its canonical producer.
        mismatches = conn.execute("""
            WITH latest AS (
              SELECT route_id,MAX(weekday_boardings) value FROM ridership_snapshots
              WHERE period=(SELECT MAX(period) FROM ridership_snapshots) GROUP BY route_id
            ), memberships AS (
              SELECT DISTINCT pm.physical_stop_id,r.route_id FROM physical_stop_members pm
              JOIN stop_gtfs_status s ON s.physical_stop_id=pm.physical_stop_id AND s.current_gtfs=1
              JOIN stop_routes sr ON sr.stop_id=pm.bus_stop_id JOIN routes r ON r.id=sr.route_id
            ), totals AS (
              SELECT m.physical_stop_id,SUM(l.value) value FROM memberships m
              LEFT JOIN latest l ON l.route_id=m.route_id GROUP BY m.physical_stop_id
            )
            SELECT COUNT(*) FROM opportunity_assessments a
            JOIN stop_gtfs_status s ON s.physical_stop_id=a.physical_stop_id AND s.current_gtfs=1
            LEFT JOIN totals t ON t.physical_stop_id=a.physical_stop_id
            WHERE ABS(COALESCE(a.combined_route_weekday_boardings,0)-COALESCE(t.value,0))>0.01
        """).fetchone()[0]
        return dict(active_stops=len(rows), usable=sum(r['exposure_score'] is not None for r in rows),
                    without_usable_data=[brief(r) for r in rows if r['exposure_score'] is None],
                    bands=dict(Counter(r['exposure_band'] for r in rows)),
                    top_20_exposure=[brief(r) for r in top],
                    top_20_route_count=[brief(r) for r in connections],
                    overlap=sorted({r['physical_stop_id'] for r in top} & {r['physical_stop_id'] for r in connections}),
                    assessment_source_mismatches=mismatches, derivation_seconds=round(elapsed, 4),
                    route_count_distribution=dict(sorted(Counter(r['active_route_count'] for r in rows).items())),
                    routes=len(map_payload(conn, 'highest')['routes']),
                    source_period=conn.execute('SELECT MAX(period) FROM ridership_snapshots').fetchone()[0],
                    integrity_check=conn.execute('PRAGMA integrity_check').fetchone()[0],
                    foreign_key_violations=len(conn.execute('PRAGMA foreign_key_check').fetchall()))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    output = json.dumps(audit(args.db), indent=2)
    if args.output:
        args.output.write_text(output + '\n', encoding='utf-8')
    else:
        print(output)

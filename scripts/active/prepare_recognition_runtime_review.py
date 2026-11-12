"""Package private WSGI log evidence for review; never collect, approve or enroll."""

import argparse
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.review.recognition import runtime_enrollment as enrollment
from src.review.recognition.runtime_evidence import MARKER
from src.review.recognition.rules import canonical, digest
from src.review.recognition.trust import load


MAX_LOG_LINE_BYTES = 1_000_000


def prepare_review(source, *, challenge_id, challenge_sha256, expected_generation,
                   source_binding_sha256, selected_observation_sha256=None):
    """Read a binary private-log excerpt; never discard a marked record."""
    records = []
    while True:
        raw = source.readline(MAX_LOG_LINE_BYTES + 1)
        if not raw:
            break
        if len(raw) > MAX_LOG_LINE_BYTES:
            raise ValueError('log_line_too_large')
        line = raw.decode('utf-8')
        if MARKER not in line:
            continue
        prefix, separator, payload = line.partition(MARKER)
        if (line.count(MARKER) != 1 or (prefix and not prefix[-1].isspace())
                or not payload or not payload[0].isspace()):
            raise ValueError('malformed_evidence_line')
        record = load(payload.strip())
        observation = enrollment.validate_observation(record)
        expected = dict(challenge_id=challenge_id, challenge_sha256=challenge_sha256,
                        source_generation=expected_generation,
                        source_binding_sha256=source_binding_sha256)
        if any(observation[key] != value for key, value in expected.items()):
            raise ValueError('evidence_scope_mismatch')
        records.append(record)
        if len(records) > enrollment.MAX_OBSERVATIONS:
            raise ValueError('too_many_observations')
    if not records:
        raise ValueError('no_runtime_observations')
    if selected_observation_sha256 is None:
        if len(records) != 1:
            raise ValueError('explicit_observation_selection_required')
        selected_observation_sha256 = records[0]['observation_sha256']
    review = dict(format=enrollment.REVIEW_FORMAT, observations=records,
                  selected_observation_sha256=selected_observation_sha256)
    return enrollment.parse_review(canonical(review))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--private-log', type=Path, required=True,
                        help='authenticated private WSGI log excerpt for this challenge')
    parser.add_argument('--challenge-id', required=True)
    parser.add_argument('--challenge-sha256', required=True)
    parser.add_argument('--expected-generation', type=int, required=True)
    parser.add_argument('--source-binding-sha256', required=True)
    parser.add_argument('--selected-observation-sha256',
                        help='required when the excerpt contains multiple observations')
    parser.add_argument('--output', type=Path, required=True,
                        help='absolute new review path; existing files are never overwritten')
    args = parser.parse_args(argv)
    try:
        if not args.private_log.is_absolute() or not args.output.is_absolute():
            raise ValueError('absolute_paths_required')
        with args.private_log.open('rb') as source:
            review = prepare_review(source, challenge_id=args.challenge_id,
                challenge_sha256=args.challenge_sha256, expected_generation=args.expected_generation,
                source_binding_sha256=args.source_binding_sha256,
                selected_observation_sha256=args.selected_observation_sha256)
        # Exclusive creation refuses existing files, hard links and symlinks,
        # including either database or the input log. No database is opened.
        serialized = canonical(review) + '\n'
        result = canonical(dict(review_sha256=digest(review),
            selected_observation_sha256=review['selected_observation_sha256']))
        descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, 'w', encoding='utf-8', newline='\n') as output:
            output.write(serialized)
    except (OSError, ValueError, TypeError):
        parser.exit(1, 'Review preparation failed; no approval or enrollment performed.\n')
    print(result)


if __name__ == '__main__':
    main()

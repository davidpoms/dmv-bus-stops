"""Test-only external process bound; never interprets timeout as authority expiry."""

import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
import time


MARKER = 'Z18_CHILD_REPORT '
TIMEOUT_SECONDS = 360
CLEANUP_SECONDS = 5
MAX_OUTPUT_BYTES = 256 * 1024
MAX_REPORTS = 32


def run_child(command, *, timeout=TIMEOUT_SECONDS, cleanup_timeout=CLEANUP_SECONDS, env=None):
    """Bound child wait and cleanup; output is a snapshot, never an EOF drain.

    Native process creation/termination, filesystem calls and OS scheduling cannot
    be preempted by a Python deadline. No Python wait below is unbounded.
    """
    for value in (timeout, cleanup_timeout):
        if type(value) not in (int, float) or not math.isfinite(value) or value <= 0:
            raise ValueError('finite_positive_diagnostic_budget_required')
    started = time.monotonic()
    child_deadline = started + timeout
    termination_deadline = child_deadline + cleanup_timeout * 0.4
    reap_deadline = child_deadline + cleanup_timeout * 0.6
    output_deadline = child_deadline + cleanup_timeout * 0.8
    parent_deadline = child_deadline + cleanup_timeout
    timings = {}
    def mark(name):
        timings[name] = time.monotonic() - started
    def remaining(deadline):
        return max(0, deadline - time.monotonic())
    def wait_until(deadline):
        # Short nonblocking polls avoid one native long-timeout wait swallowing
        # the entire cleanup/output budget. No pipe/EOF drain or unbounded wait.
        while process.poll() is None:
            left=remaining(deadline)
            if left<=0:raise subprocess.TimeoutExpired(command,timeout)
            time.sleep(min(0.025,left))
    timed_out = False
    termination_error = None
    reports = []
    output_status = 'unavailable'
    output_truncated = False
    process = None
    # File creation directly in the verified writable repository root avoids the
    # environment's restricted Temp/0700 directories. No tempfile policy changes.
    root = Path(__file__).resolve().parents[1]
    with tempfile.NamedTemporaryFile(mode='w+b', prefix='.recognition-harness-',
                                     suffix='.log', dir=root) as output:
        # Independent read handle: seeking must not move a descendant's write
        # position. O_TEMPORARY shares deletion on Windows; final handle closure
        # removes the file even when a descendant outlives its original parent.
        flags = os.O_RDONLY | getattr(os, 'O_BINARY', 0)
        if os.name == 'nt':
            flags |= os.O_TEMPORARY
        with os.fdopen(os.open(output.name, flags), 'rb') as reader:
            mark('launch_start')
            process = subprocess.Popen(command, stdout=output, stderr=output, env=env,
                                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            mark('launch_end')
            try:
                mark('child_wait_start')
                try:
                    wait_until(child_deadline)
                    timed_out = time.monotonic() >= child_deadline
                except subprocess.TimeoutExpired:
                    timed_out = True
                mark('child_wait_end')
            finally:
                # This also fences exceptions: never use communicate(), a pipe
                # reader thread, or wait() without an explicit remaining budget.
                if process.poll() is None:
                    mark('termination_start')
                    try:
                        process.kill()
                    except OSError as error:
                        termination_error = type(error).__name__
                    mark('termination_requested')
                    try:
                        wait_until(termination_deadline)
                    except subprocess.TimeoutExpired:
                        pass
                    mark('termination_wait_end')
                mark('reap_start')
                try:
                    wait_until(reap_deadline)
                except subprocess.TimeoutExpired:
                    pass
                mark('reap_end')
                if process.returncode is not None:
                    mark('direct_child_exit_observed')
            mark('output_start')
            if time.monotonic() < output_deadline:
                try:
                    size = os.fstat(reader.fileno()).st_size
                    output_truncated = size > MAX_OUTPUT_BYTES
                    reader.seek(max(0, size - MAX_OUTPUT_BYTES))
                    # Fixed snapshot length: no waiting for EOF or later writes.
                    data = reader.read(min(size, MAX_OUTPUT_BYTES))
                    output_status = 'snapshot'
                    for line in data.decode('utf-8', errors='replace').splitlines():
                        if time.monotonic() >= output_deadline:
                            output_status = 'collection_deadline'
                            break
                        if line.startswith(MARKER):
                            try:
                                report = json.loads(line[len(MARKER):])
                            except (ValueError, RecursionError):
                                continue
                            if isinstance(report, dict):
                                reports.append(report)
                                reports = reports[-MAX_REPORTS:]
                except OSError:
                    output_status = 'collection_error'
            else:
                output_status = 'collection_deadline'
            mark('output_end')
    mark('cleanup_end')
    elapsed = time.monotonic() - started
    reaped = process.returncode is not None
    return dict(status='subprocess_timeout' if timed_out else
                       'child_exited' if reaped else 'cleanup_incomplete',
                exit_code=process.returncode, pid=process.pid, reaped=reaped,
                termination_requested='termination_requested' in timings,
                termination_error=termination_error, elapsed_seconds=elapsed,
                parent_bound_exceeded=time.monotonic() > parent_deadline,
                cleanup_complete=reaped, output_status=output_status,
                output_truncated=output_truncated, reports=reports, timings=timings,
                deadlines_seconds=dict(child=timeout,
                    termination=timeout + cleanup_timeout * 0.4,
                    reap=timeout + cleanup_timeout * 0.6,
                    output=timeout + cleanup_timeout * 0.8,
                    parent_return=timeout + cleanup_timeout),
                cleanup_budget_seconds=cleanup_timeout)


def observe_consent(fresh, utc_now, records):
    """Wrap the real predicate without exporting artifacts, tokens or state."""
    def observed(state, artifact):
        record = dict(issued_at=artifact.get('issued_at_utc'),
                      expires_at=artifact.get('expires_at_utc'),
                      validation_start=utc_now())
        records.append(record)
        started = time.monotonic()
        try:
            return fresh(state, artifact)
        except BaseException as error:
            import re
            code = str(error)
            record.update(exception_class=type(error).__name__,
                          error_code=code if re.fullmatch(r'[a-z][a-z0-9_]{0,159}', code) else None)
            raise
        finally:
            record.update(validation_end=utc_now(), monotonic_elapsed_seconds=time.monotonic()-started)
    return observed

"""Read-only runtime-profile SQLite capability probes; no SQL fallback."""

import platform
import sqlite3

from .trust import require


ERROR = 'runtime_profile_requires_sqlite_json_arrow_operators_sqlite_3_38_0_or_later'
_JSON = '{"inode":18446744073709551615,"label":"probe"}'


def inspect_connection(conn):
    """Probe the actual connection, preserving unsigned inode JSON as text."""
    operators = {}
    for operator, path, expected in (
            ('->', '$.inode', '18446744073709551615'),
            ('->>', '$.label', 'probe')):
        try:
            value = conn.execute('SELECT ? '+operator+' ?', (_JSON, path)).fetchone()[0]
            operators[operator] = type(value) is str and value == expected
        except sqlite3.Error:
            operators[operator] = False
    supported = all(operators.values())
    return dict(python_version=platform.python_version(),
        sqlite_runtime_version=conn.execute('SELECT sqlite_version()').fetchone()[0],
        sqlite_library_version=sqlite3.sqlite_version,
        required_capability='JSON -> and ->> operators; exact raw JSON unsigned inode text',
        minimum_standard_sqlite_version='3.38.0', operators=operators,
        supported=supported, error=None if supported else ERROR)


def require_runtime_profile(conn):
    require(inspect_connection(conn)['supported'], ERROR)


def inspect_runtime():
    """No database path accepted: only a fresh in-memory connection is opened."""
    conn = sqlite3.connect(':memory:')
    try:
        return inspect_connection(conn)
    finally:
        conn.close()

"""Reuse report reads inside a caller-owned, locked validation transaction."""

from contextlib import contextmanager
import sqlite3

from .schema import connection


@contextmanager
def report_connection(database):
    if not isinstance(database, sqlite3.Connection):
        with connection(database) as conn:
            yield conn
        return
    if not database.in_transaction:
        raise ValueError("report_requires_transaction")
    # Reports may SELECT/inspect PRAGMAs only; they cannot commit the writer's
    # transaction, change schema, or mutate either the ledger or application.
    allowed = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION,
               sqlite3.SQLITE_RECURSIVE}
    def authorize(action, arg1, arg2, db, trigger):
        if action in allowed or (action == sqlite3.SQLITE_PRAGMA and
                                 arg1.lower() in {"table_info"}):
            return sqlite3.SQLITE_OK
        return sqlite3.SQLITE_DENY
    database.set_authorizer(authorize)
    try:
        yield database
    finally:
        database.set_authorizer(None)

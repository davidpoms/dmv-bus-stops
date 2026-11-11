# Runtime-profile SQLite capability preflight

The extension installer now checks the actual connection before extension DDL.
It requires SQLite JSON `->` and `->>` support (standard SQLite 3.38.0 or later),
including exact raw JSON text for inode `18446744073709551615`. Failure raises:

```text
runtime_profile_requires_sqlite_json_arrow_operators_sqlite_3_38_0_or_later
```

Schema definitions, triggers, inode representation and migration transactions
are unchanged. There is no fallback to numeric casts or `json_extract()`.
Neither lifetime policy nor issuer/finalizer controls change.

From the updated checkout, with the same Python interpreter/environment that
runs the migration and application, run this database-free diagnostic:

```bash
python -B scripts/active/inspect_recognition_sqlite.py
```

It opens only `:memory:` and prints Python/SQLite versions, individual operator
results, exact-inode capability and an overall `supported` result. It accepts no
database/key paths, reads no credentials and performs no production operation.
A shell `sqlite3 --version` alone does not establish Python's linked capability.

If `supported` is false, stop. The environment needs a compatible Python/SQLite
runtime before this unchanged schema can be installed; installing this preflight
alone does not supply missing operators. Do not retry migration as a capability
test. Runtime/deployment changes require a separate deliberate operation.

The previously reported failed production migration was verified rolled back to
generation 3/v2/NOT_ACTIVATED. This local change does not modify that state or
authorize migration, enrollment, activation or capture configuration changes.

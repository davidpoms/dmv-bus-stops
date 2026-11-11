# Read-only filesystem-rebind eligibility inspection

Run from the updated checkout using its Python environment:

```bash
python -B scripts/active/manage_recognition_administration.py inspect-filesystem-rebind \
  --target /home/davidpoms/dmv_bus_stops.db \
  --control /home/davidpoms/recognition-admin-control.db \
  --expected-generation 2
```

These paths and generation are the owner's previously reported selection. Use
the actual intended paths and independently expected generation. No key-file,
owner credential, operator or reason is required for this read-only action.

The JSON reports recorded and observed identities separately, complete binding
and audit-chain checks, schema hashes, logical installation IDs, owner role and
verification status, current generation, binding digest and target preview digest.
It uses the existing administration validation kernels and read-only/query-only
connections. It does not read the admin key, write either database, append an
audit, advance generation, change activation, or invoke rebind.

`ELIGIBLE_FOR_REBIND` means all inspected technical prerequisites passed: valid
v2 history/schema, expected generation, unchanged host/path/inode/schema/logical
IDs, verified owner, and at least one changed device number. Only device numbers
may differ. A v3 binding is not eligible. `NOT_ELIGIBLE_FOR_REBIND` lists exact
failed checks under `failed_conditions`; stop and investigate those failures.
An unreadable or invalid observation fails closed. Nothing is repaired or
normalized. `target_sha256` is the current target-only preview digest; it is not
an eligibility decision. `binding_sha256` identifies the inspected binding.

This is advisory and does **not** authorize rebind. The calling Bash process may
observe a different filesystem identity from WSGI. Read-only snapshots do not
reserve both databases atomically or prove that later write reservations will
succeed. A second snapshot detects observed changes but cannot establish future
continuity. Workers and filesystem replacement must be quiesced as required by
the [existing rebind ceremony](recognition-filesystem-rebind-slice-h.md), which
must independently repeat its protected checks, operator/reason and preview
confirmation. This command performs none of that ceremony.

No production rebind, migration, enrollment or activation is authorized by this
diagnostic. Keep `LIVE_RECOGNITION_CAPTURE` unchanged.

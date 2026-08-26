# Archived scripts

This directory preserves only selected historical migration records whose old schema
changes may still help explain the current database. It is not a supported executable
migration set or a substitute for Git history.

- Do not run an archived script against any database merely because its name
  resembles a current task.
- Files may depend on old schemas and may not compile or run.
- Supported compilation covers `src`, `scripts/active`, `scripts/diagnostics`, and
  `tests` only.
- Current maintainer commands belong in `scripts/active` and must document their
  database target, mutation behavior, and safe invocation.
- Prefer Git history for deleted patch, experiment, debug, and fix implementations.
- Never use these files for production operations.

Historical migration records should remain archived rather than being silently
deleted or promoted back to active use.

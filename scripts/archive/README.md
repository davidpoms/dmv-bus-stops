# Archived scripts

This directory preserves one-off patches, historical migrations, experiments,
and forensic audit material so past data/code changes remain understandable.
It is not a supported executable migration set.

- Do not run an archived script against any database merely because its name
  resembles a current task.
- Some files are incomplete patch artifacts and intentionally do not compile.
- Supported compilation covers `src`, `scripts/active`, and `tests` only.
- Current maintainer commands belong in `scripts/active` and must document their
  database target, mutation behavior, and safe invocation.
- Inspect Git history and current producers before adapting anything here.

Historical migration records should remain archived rather than being silently
deleted or promoted back to active use.

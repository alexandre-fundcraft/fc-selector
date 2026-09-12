# Verification: simplify-query-execution

## Scope and status
All ten implementation tasks completed locally. Public import paths and methods retained through explicit compatibility boundaries. SQLAlchemy is not implemented; PostgreSQL is not claimed as tested. No commit, push, PR update, merge or archive performed for this change.

## Fail-first evidence
- Mixed SQL parameter list/tuple cases failed with TypeError; all four combinations now pass.
- Executor reuse and pure validation failed because wildcard/nested selection mutated callers; now pass.
- Detached builder regression failed because frozen AST dataclasses contain mutable List.val arrays shared across builds; now passes.
- Generic projection test failed with missing from_object; now projects objects/mappings with ORM/protocol imports blocked.
- Django execution architecture test failed on the visitor's OData import; now executes a real SQLite filter and DTO materialization with OData/DRF imports blocked.
- One not-found test mocked the previous internal call. Updated the mock to prepared execution; observable 404 assertion unchanged.

## Contracts
- 24-case parity matrix: text/fluent x standard/hybrid x DTO/dict x forward/children/per-parent-limit shapes. Exact output and 1 or 2 SQL queries for three roots.
- One preparation per materialization, builder replacement and lazy custom parser checks.
- Existing audit tests preserve field restrictions, secrets, authorization, nested pagination, scope/count and SQL counts.
- 37 new cases: 34 execution contracts and 3 fresh-process architecture cases.

## Final local validation
- Python 3.11.15 / Django 5.2.11: **1208 passed**, including performance test functions with benchmark timing disabled.
- **94% coverage**, 3357 statements, 200 missed.
- Ruff passed; Mypy passed (65 library files); strict MkDocs passed.
- Strict OpenSpec all validation passed; git diff --check passed.
- pyproject.toml and uv.lock unchanged; --no-migrations retained.

## Explicit compatibility matrix
Command: `uv run --frozen --isolated --python VERSION --with django==SPEC pytest tests/ --ignore=tests/performance/ --benchmark-disable`.
Ten performance tests excluded here, as in CI. All six processes exited 0 on local macOS/SQLite. Remote Linux checks will run after publication; not yet verified for this uncommitted change.

| Python | Installed Django | Result | Duration |
| --- | --- | --- | --- |
| 3.11.15 | 4.2.20 | 1198 passed | 8.60 s |
| 3.11.15 | 5.0.14 | 1198 passed | 9.43 s |
| 3.11.15 | 5.2.11 | 1198 passed | 10.74 s |
| 3.12.13 | 5.2.17 | 1198 passed | 11.29 s |
| 3.12.13 | 6.0.2 | 1198 passed | 12.61 s |
| 3.13.13 | 6.0.2 | 1198 passed | 12.92 s |

Compatible locked versions may be reused; environments may resolve different patch versions on the same explicit release line. CI prints/asserts the line. These compatibility tests do not recommend deploying old versions.

## Boundaries
- Core builder has one state per option and detached results; only legacy text methods cross the lazy compat boundary.
- DTO from_object takes neutral intents and an optional value reader; no Django managers, prefetch or OData options in generic projection.
- Core collection/projection policies and AST rewriting are reusable by future adapters.
- Direct Django intent execution/materialization works without OData/DRF imports.
- OData owns parsing/export; historical dto_options, AST helpers and path imports remain compatibility delegates/re-exports.
- Shared DTOs/selectors moved into integration/support.

## Release work remaining
Review/commit/push, observe remote checks, then archive OpenSpec when requested. PR #5 has not received this change yet.

## Why
Remote CI exposes a Django 6 SQL parameter incompatibility. Duplicated normalization, execution selection and builder representations make equivalent queries harder to maintain safely.

## What Changes
- Fix not-equal SQL parameter handling across supported Django versions.
- Prepare a private normalized intent without modifying caller-owned queries; validate independently.
- Choose standard or hybrid execution once; preserve the direct hybrid builder entry point as a compatibility wrapper.
- Consolidate QueryBuilder filter, expansion and ordering state into one representation per option while retaining lazy textual parsing and the public API.
- Isolate ORM-specific extraction and protocol parsing from the neutral core for future SQLAlchemy support, preserving compatibility entry points.
- Add parity and SQL-count regressions, shared test support, explicit Python/Django CI combinations and documented backend scope.

## Capabilities
### New Capabilities
- `reusable-query-intents`: Executing and validating queries preserves caller-owned state and equivalent public entry points.
- `django-compatibility`: Not-equal queries work across the explicitly tested framework combinations.
### Modified Capabilities
None; existing safe-selector-queries and verified-project-contract requirements remain in force.

## Impact
Executor, hybrid builder, selector, DRF retrieval, QueryBuilder, test support and GitHub Actions. No new production dependencies, no public API removals, no change to --no-migrations. No automatic merge or publication.

## Why

The audit reproduced data disclosure, missing object authorization and divergent query semantics despite a passing test suite. Fix these boundaries before relying on selectors for untrusted API requests.

## What Changes

- **BREAKING**: consistently enforce selector field policies, collection limits and DRF object permissions; exclude passwords and write-only fields from serialization.
- Preserve filters, URL literals, nested expansion options, ordering and projections across fluent/string and standard/hybrid execution.
- Remove deferred-field N+1 queries and align metadata with DTO fields and aliases.
- Correct documentation for unsupported management commands and enable blocking CI quality checks.
- Preserve the intentional pytest `--no-migrations` configuration. No new runtime dependencies or broad rewrite.

## Capabilities

### New Capabilities
- `safe-selector-queries`: validated, authorized and consistent selector execution and serialization.
- `verified-project-contract`: accurate metadata/documentation and runnable quality gates.

### Modified Capabilities

None; this repository had no OpenSpec specifications.

## Impact

Core query builder, OData parsers, Django selector/executors, DRF integration, metadata, example, tests, Makefile and CI. Consumers depending on unbounded collections, exposed secrets or ignored restrictions must migrate to the corrected contract.

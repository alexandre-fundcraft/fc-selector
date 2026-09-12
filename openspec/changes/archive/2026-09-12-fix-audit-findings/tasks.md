## 1. Query contract
- [x] 1.1 Add failing regressions for filter composition, URL decoding, nested options and pagination; fix shared query conversion and verify those tests pass.
- [x] 1.2 Add policy regressions for select/filter/order/expand and aliases; validate both execution modes and verify tests pass.

## 2. Security and API
- [x] 2.1 Add failing serialization regressions; enforce password, write-only and nested exclusions; verify anonymous example exposure is closed.
- [x] 2.2 Add failing API regressions for object permissions, scope, counts and malformed inputs; fix DRF integration and verify tests pass.

## 3. Expansion and performance
- [x] 3.1 Add failing parity regressions for hidden PK, per-parent pagination, fluent expansion and M2M ordering; fix or safely route unsupported hybrid shapes and verify both modes.
- [x] 3.2 Add a standard forward-expansion query-count regression and eliminate deferred scalar fetches; verify bounded query count.

## 4. Public contract and verification
- [x] 4.1 Add metadata regression for DTO aliases and protected fields; align generated metadata and verify tests pass.
- [x] 4.2 Replace absent-command documentation, correct hybrid/pagination claims and fix type/lint gates; verify documentation and local checks.
- [x] 4.3 Add CI checks and run full tests, Ruff, Mypy and OpenSpec strict validation; record evidence and remaining limitations.

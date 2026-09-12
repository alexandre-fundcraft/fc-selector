# Verification — fix-audit-findings

## Scope and evidence

Implemented all nine tasks. The intentional pytest `--no-migrations` option and
`pyproject.toml` are unchanged. No new runtime dependencies, database migrations,
commits or deployments were made.

`tests/test_audit_regressions.py` adds **56 regression cases**. The initial batch
had 33 failures and five passes before fixes; subsequent edge cases were also
reproduced before their corrections.

| Contract | Regression evidence |
|---|---|
| Private output | write-only fields, nested password, DTO exclusions, explicit nested serializer, anonymous example endpoint |
| Authorization | denied model object returns 403; queryset and filter backend scope applies to list/retrieve/count |
| Query semantics | mixed AST/string filters, non-mutating PK lookup, nested options, encoded literals and dotted aliases |
| Policies | select/filter/order/expand restrictions, default/wildcard projections, nested allowlists, negative nested sorting |
| Pagination | offset-only limits, capped limits, zero pages, independent counts, encoded links, invalid scalar-expansion pagination |
| Expansion | per-parent pagination through selector and direct hybrid builder; omitted PK retains children; M2M ordering; fluent/deep forward expansions |
| Performance | three forward-expanded roots: one SQL query; three deep-expanded roots: two queries, not five |
| Metadata | only exposed DTO fields with API aliases; protected fields omitted |
| Quality gates | injected Ruff failure → make exit 2; Mypy failure → exit 2; both passing → exit 0 |

## Commands

```sh
.venv/bin/python -m pytest tests -q -o addopts='--no-migrations --tb=short' \
  --benchmark-disable --cov=fc_selector --cov-report=term
.venv/bin/ruff check fc_selector tests
.venv/bin/mypy fc_selector --no-incremental
.venv/bin/python -m mkdocs build --strict -d build/docs-audit
openspec validate fix-audit-findings --strict
git diff --check
```

Final results: **1,171 passed**, **94% statement coverage**, Ruff clean, Mypy clean
(59 library files), strict documentation build and strict OpenSpec validation
successful. Tests include the performance directory with benchmark timing disabled.

## Compatibility notes

- Local validation used Python 3.11 and Django 5.2.11. The added CI matrix targets
  Python 3.11–3.13; remote CI has not been executed in this session.
- Complex expansion shapes use standard ORM fallback; sliced collection prefetch
  requires a database supporting window functions. Pagination on scalar relations
  is rejected as a client error.
- Fluent AST builders must use `.build()`; textual conversion now fails explicitly
  rather than silently omitting fluent options.
- Low-level `query`/`execute` remain lazy and do not add collection defaults.
- Additional nested serializer policy is explicit via `Meta.nested_serializers`;
  passwords and DTO-level exclusions are protected without registration.
- Missing generator/seed commands were removed from instructions instead of adding
  a new generator. DTOs and selectors are defined explicitly.
- Changes remain uncommitted and the completed OpenSpec change is retained for review.

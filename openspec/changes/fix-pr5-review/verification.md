# Verification

## Regression evidence
- Before implementation: all 17 initial cases in tests/test_pr5_regressions.py failed (aliases across four entry points/two modes; properties/two modes; invalid related paths with and without allowlists; annotation support).
- After implementation and expanded coverage: 30 focused tests pass, including collection aliases, multilevel neutral mapping without mutation, and both retrieve execution stages.

## Checks
- Full configured suite: 1232 passed, 94% coverage (pytest --cov=fc_selector --cov-report=term --benchmark-disable).
- Six isolated compatibility runs: 1222 passed each (tests/, excluding performance), Python/Django: 3.11/4.2.20, 3.11/5.0.*, 3.11/5.2.*, 3.12/5.2.*, 3.12/6.0.*, 3.13/6.0.*.
- Ruff check: pass. Changed Python files formatting: pass.
- Full-repository format check reports five pre-existing unrelated files (core/utils.py, django/utils/paths.py, protocols/odata/parsers/filter/{rewrite,utils}.py, tests/test_hybrid_values_builder.py); left unchanged to avoid unrelated churn.
- Mypy: 65 source files pass.
- MkDocs strict: pass.
- OpenSpec strict validation: pass.
- git diff --check: pass.

## Boundaries
Core receives plain mapping trees and remains independent of Django/OData; existing architecture boundary tests pass. No backend files touched, no PostgreSQL validation claimed, no merge or archive performed.

## Publication
Implementation commit: 74f66b6, pushed to PR 5. Replied to all five Copilot threads with the fix and regression evidence. Threads remain open for reviewer confirmation.

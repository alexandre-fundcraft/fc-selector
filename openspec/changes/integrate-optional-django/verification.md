# Verification

## Source and review
Adapted PR #3 commit 8f99e59 into PR #5, preserving current docs and CI. This is a port, not a merge to main or closure of PR #3.

Copilot comments:
- 3942984639: explicit Django/DRF/spectacular dev dependencies, no fc-selector self-dependency. Metadata regression keeps extra/dev aligned.
- 3942984691: guard explicitly blocks drf_spectacular as well as Django/DRF. Negative tests prove each blocked import fails; normal probe passes.
- 3942984722: README and installation requirements enumerate all three adapter packages and versions.

## Evidence
- Metadata test failed before packaging changes; now passes.
- Full suite: **1211 passed**, **94% coverage** (3357 statements,200 missed).
- Ruff, Mypy(65 files), strict MkDocs, OpenSpec strict all, git diff --check pass.
- uv lock and uv sync --frozen --group dev pass; lock changes only dependency grouping/extra markers, not package upgrades.
- Built wheel base installation via uv run --no-project --isolated --with WHEEL python -I tests/test_core_without_django.py passes; verifies adapter packages absent and generic DTO/fluent/parser functionality. Only wheel+sly installed.
- Installed WHEEL[django] in another isolated environment: Django, DRF, spectacular and executor import successfully (Django5.2.17).
- CI now builds/tests standalone wheel with python -I, preventing source-tree imports from masking packaging defects.
- Existing --no-migrations unchanged.

## Final local compatibility matrix (SQLite/macOS)
Each run excludes the ten performance test functions, matching CI.

| Python | Django | Result |
| --- | --- | --- |
| 3.11.15 | 4.2.20 | 1201 passed |
| 3.11.15 | 5.0.14 | 1201 passed |
| 3.11.15 | 5.2.11 | 1201 passed |
| 3.12.13 | 5.2.17 | 1201 passed |
| 3.12.13 | 6.0.2 | 1201 passed |
| 3.13.13 | 6.0.2 | 1201 passed |

## Publication
All implementation/testing complete. Commit/push to PR #5 and a PR #3 cross-reference are tracked in task4. Neither PR is merged or closed; neither OpenSpec change is archived. Remote checks run after push.

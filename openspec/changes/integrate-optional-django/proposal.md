## Why
PR #3 remains unmerged and has three unresolved Copilot comments. Runtime decoupling in PR #5 needs matching package dependency boundaries.
## What Changes
- Port PR #3 optional Django extra into PR #5, preserving its newer docs and CI.
- Avoid the dev self-dependency; explicitly list adapter requirements in dev.
- Block Django, DRF and drf-spectacular in isolation tests; verify real wheel installation without the extra.
- Document all extra dependencies and repository installation commands.
## Capabilities
### New Capabilities
- `optional-django-installation`: Base installs omit adapter dependencies; Django extra and development installs retain them.
### Modified Capabilities
None.
## Impact
pyproject.toml, uv.lock, README, installation docs, tests and CI. No SQLAlchemy implementation, merge, automatic closing of PR #3 or archive.

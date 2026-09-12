## Context
PR #3 commit 8f99e59 makes the adapter optional but adds a self-dependency in dev, omits drf_spectacular from the guard and omits that dependency from requirements docs.
## Decisions
Port the five-file change into PR #5 rather than overwrite its updated documentation. Keep base dependencies to sly; list Django/DRF/spectacular in the optional extra and dev group. A small metadata contract test ensures these lists stay aligned without self-reference.
Use the original subprocess probe extended to block all adapter packages. Add a real wheel install CI smoke check under python -I so source-tree imports cannot mask packaging errors. Keep pytest --no-migrations unchanged.
## Validation
Fail-first metadata contract; full tests, lint/types/docs/OpenSpec; locked resolution; six framework combinations; isolated wheel installations both without and with Django extra.

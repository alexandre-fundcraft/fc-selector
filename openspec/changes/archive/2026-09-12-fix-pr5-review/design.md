## Context
Copilot review on PR 5 head 87776fb reported five issues; static tracing confirmed all five and 17 regression cases failed before implementation.

## Goals / Non-Goals
Goals: preserve aliases at every expansion level, materialize properties correctly, fail early for nonexistent related paths, prove error mapping, align documentation.
Non-goals: new ORM adapters, backend integration, query performance redesign.

## Decisions
Use plain nested mapping options in from_object; Django executor derives them from per-relation configuration. Core remains ORM/protocol independent. Both selector projection and direct executor materialization consume these mappings. Dictionary property requests bypass values-only projection. Traverse model relationships for multi-segment paths; actual queryset annotations and explicitly allowed single annotation names remain supported for compatibility.

## Risks / Trade-offs
Related field checks intentionally reject nonexistent paths before query evaluation. Per-relation alias options must not mutate caller intents. Property fallback may instantiate models; correctness takes precedence over values optimization.

## Migration Plan
Add failing regressions, fix shared paths, verify focused and full tests, lint/types/docs and compatibility matrix; publish to existing PR without merge or archive.

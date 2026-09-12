## Context

See proposal.md. The same request currently follows distinct parsing, validation and DTO projection paths. Existing tests use SQLite and intentionally disable migrations.

## Goals / Non-Goals

Goals: enforce policies at shared boundaries; use the intent for execution and DTO options; retain queryset scoping and object permissions; prove fixes with regressions.
Non-goals: new query languages, runtime dependencies, generated-code infrastructure, changing the migration configuration or rewriting the architecture.

## Decisions

- Use the existing OData parser once for raw query strings; combine filters as AST when either side is fluent. Derive nested DTO options from intent rather than reparsing the original builder.
- Primary-key lookups scope the queryset with the model PK rather than injecting a client filter, so they support string keys and filter policies without mutating the builder.
- Enforce selector collection defaults in all collection helpers. Low-level execute/query remain composable queryset operations without implicit pagination, and count excludes pagination. Document this distinction.
- Validate field policies in the executor before either execution mode, resolve aliases consistently, and pass nested relation policy separately from root policy.
- DTO-level exclusions apply at every serialization depth; password is excluded by default. Explicit nested serializers can provide further output policy without global auto-discovery.
- DRF retrieves the scoped model before checking object permissions; serialization only happens after authorization. Lists use view queryset/filter backends, with scoped counts.
- Keep the fast hybrid path for supported shapes. Use standard prefetch for per-parent pagination and deep forward expansions rather than implement another window-query engine. Preserve hidden grouping keys until children are attached.
- Metadata reflects DTO names/aliases; remove claims and instructions for absent code-generation/seed commands instead of building an unrequested generator.

## Risks / Trade-offs

- Correct restrictions reject formerly accepted queries → regression tests and migration notes.
- Complex expansions may use standard ORM fallback → query-count regression and explicit documentation; correctness precedes speed.
- DRF model permissions may inspect fields absent from DTOs → authorize the model, not the DTO.

## Migration Plan

Run regression tests then full suite, Ruff, Mypy, docs and OpenSpec validation. No database migrations. Ship as a contract-hardening release; rollback via source revert if needed, without re-exposing vulnerable endpoints.

Text conversion of fluent AST builders now raises a clear error directing callers to `.build()`, rather than silently dropping filters. Validation canonicalizes implicit allowed-field projections, including nested relation policies.

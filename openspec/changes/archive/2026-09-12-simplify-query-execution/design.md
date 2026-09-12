## Context
The selector normalizes selection, then executor validation normalizes it again. Hybrid execution re-enters the executor through its public builder. QueryBuilder maintains parallel text and fluent slots. Local Django 5.2 passes while Django 6 fails tuple/list SQL concatenation.

## Goals / Non-Goals
Implement all six follow-up recommendations now, including builder consolidation. Preserve lazy QuerySets, collection defaults, nested policies and direct-builder compatibility. Future SQLAlchemy support is an explicit design constraint. No SQLAlchemy implementation yet, no rewrite, strategy framework, cache or new production dependency.

## Decisions
- Executor.prepare makes a copy, normalizes projections recursively and validates without altering the caller. Prepared execution methods avoid repeated preparation at selector and nested prefetch boundaries. Selector alone applies collection pagination/default ordering.
- Executor owns hybrid eligibility and fallback. HybridValuesBuilder.execute remains a thin public wrapper; its internal prepared builder only constructs results.
- QueryBuilder stores one tagged union per filter/expand/order option (text or AST/fluent objects), not synchronized pairs. Text remains lazily parsed to preserve injection and error timing. Each build returns detached intent data; textual export continues to reject unrepresentable fluent queries.
- Move reusable DTOs/selectors into existing tests/integration/support, not another abstraction package.
- CI has explicit compatible Python/Django combinations including minimum Django 4.2.20, 5.0, 5.2 and 6.0. Keep a frozen-lock quality job; override Django in isolated test runs. SQLite is the verified backend; PostgreSQL is not claimed without consumer requirements/infrastructure.

## Risks / Trade-offs
Private-method tests may need adjustment but observable behavior is authoritative. Direct builder callers retain their filtered/ordered queryset contract. Nested policy validation must happen even when no database rows exist. Guard recursion before normalization recurses. Standard/hybrid projections and aliases must remain consistent.

## Validation
Fail-first tuple/list and intent non-mutation regressions, mixed builder replacement/composition checks, mode/input/output parity matrix, existing audit security and SQL-count tests. Full pytest, Ruff, Mypy, strict MkDocs and OpenSpec validation; test representative framework combinations locally where interpreters are available.

## ORM and protocol boundaries (user requirement)
Dependency direction: OData parsing -> neutral QueryIntent/AST <- ORM adapters. SQLAlchemy must eventually consume the same intents without importing Django or DRF.

- Core owns neutral query structures, fluent composition and generic projection rules. Reusable collection/projection policy helpers live in core/intent/policies.py. It must not interpret Django managers, prefetch caches, model metadata or Django lookup paths.
- OData owns text parsing and textual export. Preserve existing QueryBuilder import paths and string methods through a compatibility facade; keep the neutral fluent implementation free of OData imports. Parser injection alone is insufficient while expand parsing remains hard-coded.
- Django owns SQL compilation, field/model validation, relation loading, path translation, hybrid execution and model-to-DTO extraction. DjangoExecutor.prepare is an adapter entry point, not the owner of reusable protocol-independent policies.
- Generic DTO projection must consume plain values/objects; isolate current .all(), _prefetched_objects_cache and _odata_ handling in Django conversion. Preserve existing BaseODataDTO.from_model behavior through a clearly identified compatibility boundary rather than silently breaking clients.
- Keep collection defaults/projection policy separate from model-specific validation so another adapter can reuse policies without inheriting a Django selector.
- Do not create a speculative common ORM base class or force SQLAlchemy into QuerySet semantics. Preserve Django's lazy API and define a narrow execution contract only where current callers need it.
- Add architecture checks: neutral core and fluent queries run with Django and OData imports blocked; OData parsing runs with Django blocked; generic nested DTO projection works on plain objects/lists. Existing Django compatibility imports and behavior are tested separately and documented as compatibility surfaces, not claimed as fully neutral internals.

Current coupling confirmed in core/query_builder.py (OData parsers), core/dtos/base.py (OData options and Django manager/cache conventions), and core/utils.py (odata_path_to_django). Removing only Django imports would not satisfy this boundary.

## Implementation notes
- Existing QueryBuilder class/import paths remain; only its text methods lazily dispatch through compat to protocols/odata/builder. No extra neutral builder class or registry is needed. Each fluent option is snapshotted into its single state slot and builds are detached.
- BaseODataDTO.from_object accepts neutral intents and a callable value reader; from_model is the explicit legacy Django/OData facade. Generic traversal uses objects/mappings and dotted paths. Django's reader alone knows managers and prefetch caches.
- AST rewriting moved to core/ast/rewrite.py with legacy protocol re-exports. Django public package exports are lazy; importing a low-level executor does not initialize DRF or OData. A real SQLite query/materialization passes with OData and DRF imports blocked.
- core's old dto_options and path converter are compatibility delegates, not neutral internal operations. Adapter-owned OData selector/DRF paths import protocol export helpers directly.

"""Django executor for OData $apply (groupby/aggregate).

Translates the protocol-agnostic $apply AST (fc_selector.core.ast.nodes.Apply)
into Django .values().annotate() calls. Standard OData v4 aggregate methods
(sum, average, min, max, countdistinct, count) are always available; any
other method name is looked up in the selector's Meta.apply_aggregates. Group-by
field specs that aren't plain model fields are looked up in Meta.apply_functions
(e.g. a "quarter(created_at)"-style bucket function) — this module has no
built-in knowledge of what those might be beyond the standard OData date
functions already exposed via $filter's own function dispatch.
"""

from typing import Any, Callable

from django.db.models import Avg as _Avg
from django.db.models import Count, F, Max, Min, QuerySet
from django.db.models import Sum as _Sum

from fc_selector.core import exceptions as core_ex
from fc_selector.core.ast import nodes as ast_nodes  # NEW
from fc_selector.core.intent.models import ApplyIntent
from fc_selector.django.executor import DjangoExecutor, identifier_names  # NEW
from fc_selector.django.utils.aliases import resolve_field_alias
from fc_selector.django.visitors import AstToDjangoQVisitor

_STANDARD_AGGREGATES: dict[str, Callable[[str | None], Any]] = {
    "sum": lambda field: _Sum(field),
    "average": lambda field: _Avg(field),
    "min": lambda field: Min(field),
    "max": lambda field: Max(field),
    "countdistinct": lambda field: Count(field or "pk", distinct=True),
}


def apply_to_queryset(
    queryset: QuerySet,
    apply_intent: ApplyIntent,
    *,
    allowed_fields: list[str] | None = None,
    apply_functions: dict[str, Callable[[], Any]] | None = None,
    apply_aggregates: dict[str, Callable[..., Any]] | None = None,
    field_annotations: dict[str, Callable[[], Any]] | None = None,
    annotation_dependencies: dict[str, tuple[str, ...]] | None = None,
    field_aliases: dict[str, str] | None = None,
    filterable_fields: list[str] | None = None,
    non_filterable_fields: list[str] | None = None,
) -> QuerySet | list[dict]:
    """Apply a parsed $apply pipeline to a queryset, returning a .values(...) queryset."""
    field_annotations = field_annotations or {}
    annotation_dependencies = annotation_dependencies or {}
    apply_functions = apply_functions or {}
    apply_aggregates = apply_aggregates or {}
    apply_ast: ast_nodes.Apply = apply_intent.ast

    executor = DjangoExecutor(field_annotations=field_annotations, annotation_dependencies=annotation_dependencies)
    allowed_fields_set = set(allowed_fields) if allowed_fields is not None else None
    num_stages = len(apply_ast.transformations)

    for idx, stage in enumerate(apply_ast.transformations):
        is_last = idx == num_stages - 1
        if isinstance(stage, ast_nodes.ApplyFilter):
            referenced = list(identifier_names(stage.ast))
            queryset = executor.ensure_field_annotations(queryset, referenced)
            visitor = AstToDjangoQVisitor(
                queryset.model,
                allowed_fields=allowed_fields_set,
                field_aliases=field_aliases,
                filterable_fields=filterable_fields,
                non_filterable_fields=non_filterable_fields,
            )
            visitor.queryset_annotations.update(queryset.query.annotations)
            queryset = queryset.filter(visitor.visit(stage.ast))
            continue

        if isinstance(stage, ast_nodes.ApplyGroupBy):
            if not stage.fields and not is_last:
                raise core_ex.QueryError("A bare aggregate() must be the final transformation stage in $apply.")
            plain_fields = [f for f in stage.fields if f not in apply_functions]
            queryset = executor.ensure_field_annotations(queryset, plain_fields)
            source_fields = [s.source_field for s in (stage.aggregate or []) if s.source_field]
            queryset = executor.ensure_field_annotations(queryset, source_fields)
            res = _apply_groupby(
                queryset,
                stage,
                allowed_fields,
                apply_functions,
                apply_aggregates,
                field_aliases=field_aliases,
            )
            if isinstance(res, list):
                return res
            queryset = res
            continue

        raise core_ex.QueryError(f"Unknown $apply transformation: {type(stage).__name__}")

    return queryset


def _resolve_aggregate(
    spec: ast_nodes.ApplyAggregateSpec,
    apply_aggregates: dict[str, Callable[..., Any]],
    field_aliases: dict[str, str] | None = None,
) -> tuple[str, Any]:
    source = resolve_field_alias(spec.source_field, field_aliases) if spec.source_field else None
    if spec.method == "count":
        return spec.alias, Count("pk")
    if spec.method in _STANDARD_AGGREGATES:
        if source is None and spec.method != "countdistinct":
            raise core_ex.QueryError(f"Aggregate '{spec.method}' requires a source field.")
        return spec.alias, _STANDARD_AGGREGATES[spec.method](source)
    if spec.method in apply_aggregates:
        if source is None:
            raise core_ex.QueryError(f"Custom aggregate '{spec.method}' requires a source field.")
        return spec.alias, apply_aggregates[spec.method](F(source))
    raise core_ex.UnsupportedFunctionError(spec.method)


def _apply_groupby(
    queryset: QuerySet,
    stage: ast_nodes.ApplyGroupBy,
    allowed_fields: list[str] | None,
    apply_functions: dict[str, Callable[[], Any]],
    apply_aggregates: dict[str, Callable[..., Any]],
    field_aliases: dict[str, str] | None = None,
) -> QuerySet | list[dict]:
    field_aliases = field_aliases or {}
    if allowed_fields is not None:
        for field_spec in stage.fields:
            if field_spec not in allowed_fields and field_spec not in apply_functions:
                raise core_ex.FieldNotFoundError(field_spec, queryset.model.__name__)
        for spec in stage.aggregate or []:
            if spec.source_field and spec.source_field not in allowed_fields:
                raise core_ex.FieldNotFoundError(spec.source_field, queryset.model.__name__)

    group_values: list[str] = []
    annotations: dict[str, Any] = {}
    for field_spec in stage.fields:
        if field_spec in apply_functions:
            annotations[field_spec] = apply_functions[field_spec]()
            group_values.append(field_spec)
        else:
            orm_field = resolve_field_alias(field_spec, field_aliases)
            if orm_field != field_spec:
                annotations[field_spec] = F(orm_field)
                group_values.append(field_spec)
            else:
                group_values.append(field_spec)

    if annotations:
        queryset = queryset.annotate(**annotations)

    if not group_values:
        # Bare aggregate(...), no groupby(): a single summary row. `.values().annotate()`
        # would group by every model field instead, so use `.aggregate()` directly.
        if stage.aggregate:
            agg_kwargs = {}
            for spec in stage.aggregate:
                alias, expr = _resolve_aggregate(spec, apply_aggregates, field_aliases)
                agg_kwargs[alias] = expr
            return [queryset.aggregate(**agg_kwargs)]
        raise core_ex.QueryError("groupby fields list cannot be empty")

    queryset = queryset.values(*group_values)

    if stage.aggregate:
        agg_kwargs = {}
        for spec in stage.aggregate:
            alias, expr = _resolve_aggregate(spec, apply_aggregates, field_aliases)
            agg_kwargs[alias] = expr
        queryset = queryset.annotate(**agg_kwargs)
    else:
        queryset = queryset.distinct()

    return queryset

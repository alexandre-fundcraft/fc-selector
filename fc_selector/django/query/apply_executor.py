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
from django.db.models import Count, F, Max, Min, QuerySet, Value
from django.db.models import Sum as _Sum

from fc_selector.core import exceptions as core_ex
from fc_selector.core.ast.nodes import Apply, ApplyFilter, ApplyGroupBy
from fc_selector.core.intent.models import ApplyIntent
from fc_selector.django.visitors import AstToDjangoQVisitor

_STANDARD_AGGREGATES: dict[str, Callable[[str], Any]] = {
    "sum": lambda field: _Sum(field),
    "average": lambda field: _Avg(field),
    "min": lambda field: Min(field),
    "max": lambda field: Max(field),
    "countdistinct": lambda field: Count(field, distinct=True),
}


def apply_to_queryset(
    queryset: QuerySet,
    apply_intent: ApplyIntent,
    *,
    allowed_fields: list[str] | None = None,
    apply_functions: dict[str, Callable[[], Any]] | None = None,
    apply_aggregates: dict[str, Callable[..., Any]] | None = None,
) -> QuerySet:
    """Apply a parsed $apply pipeline to a queryset, returning a .values(...) queryset."""
    apply_functions = apply_functions or {}
    apply_aggregates = apply_aggregates or {}
    apply_ast: Apply = apply_intent.ast

    for stage in apply_ast.transformations:
        if isinstance(stage, ApplyFilter):
            queryset = queryset.filter(AstToDjangoQVisitor(queryset.model).visit(stage.ast))
            continue

        if isinstance(stage, ApplyGroupBy):
            queryset = _apply_groupby(queryset, stage, allowed_fields, apply_functions, apply_aggregates)
            continue

        raise core_ex.QueryError(f"Unknown $apply transformation: {type(stage).__name__}")

    return queryset


def _resolve_group_field(field_spec: str, apply_functions: dict[str, Callable[[], Any]]) -> tuple[str, Any]:
    """Return (output_alias, annotation_expr_or_None). A plain field has no annotation."""
    if field_spec in apply_functions:
        return field_spec, apply_functions[field_spec]()
    return field_spec, None


def _resolve_aggregate(spec, apply_aggregates: dict[str, Callable[..., Any]]):
    if spec.method == "count":
        return spec.alias, Count("pk")
    if spec.method in _STANDARD_AGGREGATES:
        if spec.source_field is None:
            raise core_ex.QueryError(f"Aggregate '{spec.method}' requires a source field.")
        return spec.alias, _STANDARD_AGGREGATES[spec.method](spec.source_field)
    if spec.method in apply_aggregates:
        if spec.source_field is None:
            raise core_ex.QueryError(f"Custom aggregate '{spec.method}' requires a source field.")
        return spec.alias, apply_aggregates[spec.method](F(spec.source_field))
    raise core_ex.UnsupportedFunctionError(spec.method)


def _apply_groupby(queryset, stage: ApplyGroupBy, allowed_fields, apply_functions, apply_aggregates) -> QuerySet:
    if allowed_fields is not None:
        for field_spec in stage.fields:
            if field_spec not in allowed_fields and field_spec not in apply_functions:
                raise core_ex.FieldNotFoundError(field_spec, queryset.model.__name__)

    group_values: list[str] = []
    annotations: dict[str, Any] = {}
    for field_spec in stage.fields:
        alias, expr = _resolve_group_field(field_spec, apply_functions)
        if expr is not None:
            annotations[alias] = expr
        group_values.append(alias)

    if annotations:
        queryset = queryset.annotate(**annotations)

    if stage.aggregate:
        agg_kwargs = {}
        for spec in stage.aggregate:
            alias, expr = _resolve_aggregate(spec, apply_aggregates)
            agg_kwargs[alias] = expr

        if not group_values:
            queryset = (
                queryset.annotate(_dummy=Value(1)).values("_dummy").annotate(**agg_kwargs).values(*agg_kwargs.keys())
            )
        else:
            queryset = queryset.values(*group_values).annotate(**agg_kwargs)
    elif group_values:
        queryset = queryset.values(*group_values).distinct()
    else:
        queryset = queryset.values()

    return queryset

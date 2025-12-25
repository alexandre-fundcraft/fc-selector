import operator
from collections.abc import Callable
from typing import Any, cast
from uuid import UUID

from django.db.models import (
    Case,
    Exists,
    F,
    Model,
    OuterRef,
    Q,
    Value,
    When,
    functions,
    lookups,
)
from django.db.models.expressions import Expression

from fc_selector.core import ast
from fc_selector.core import exceptions as core_ex
from fc_selector.core.ast import visitor

# We still use utils from parsers to manipulate AST nodes (should be moved to core later)
from fc_selector.protocols.odata.parsers.filter import utils

from .django_q_ext import NotEqual
from .utils import reverse_relationship


class AstToDjangoQVisitor(visitor.NodeVisitor):
    """
    :class:`NodeVisitor` that transforms an :term:`AST` into a Django Q
    filter object.

    Args:
        root_model: The root model of the query.
        allowed_fields: Optional set of allowed field names for security validation.
            If None, all model fields are allowed.
        field_aliases: Optional dict mapping alias names to actual model field names.
            Allows using e.g. 'client_uuid' in queries when the model field is 'client_id'.
    """

    def __init__(
        self,
        root_model: type[Model],
        allowed_fields: set[str] | None = None,
        field_aliases: dict[str, str] | None = None,
    ):
        self.root_model = root_model
        self.allowed_fields = allowed_fields
        self.field_aliases = field_aliases or {}
        self.queryset_annotations: dict[str, Expression] = {}

        # Keep track of the depth of `visit` calls, so we know when we should
        # turn the Django expression into a final `Q` object.
        self._depth: int = 0

    def _resolve_field_alias(self, field_name: str) -> str:
        """Resolve field alias to actual model field name."""
        if not self.field_aliases:
            return field_name
        # Handle nested fields (e.g., "relation__field")
        parts = field_name.split("__")
        parts[0] = self.field_aliases.get(parts[0], parts[0])
        return "__".join(parts)

    def _validate_field(self, field_name: str) -> str:
        """Validate field name for security and resolve aliases.

        Returns the resolved field name (with aliases applied).
        """
        # Block access to private/internal fields
        if field_name.startswith("_"):
            raise core_ex.InvalidFieldError(
                field_name, self.root_model.__name__, reason="access to private fields is not allowed"
            )

        # Extract base field name (before any __)
        base_field = field_name.split("__")[0]

        # Check against allowed fields if specified (use original field name for API contract)
        if self.allowed_fields is not None and base_field not in self.allowed_fields:
            raise core_ex.InvalidFieldError(
                field_name, self.root_model.__name__, reason="field is not in allowed fields list"
            )

        # Resolve alias to actual model field
        resolved_field = self._resolve_field_alias(field_name)

        # Validate that resolved field exists on the model (for simple fields only)
        # Skip validation if field is in allowed_fields (might be an annotation)
        if "__" not in resolved_field and not (self.allowed_fields is not None and base_field in self.allowed_fields):
            from fc_selector.django.utils.introspection import get_field_safe

            if not get_field_safe(self.root_model, resolved_field):
                raise core_ex.InvalidFieldError(
                    field_name, self.root_model.__name__, reason="field does not exist on model"
                )

        return resolved_field

    def visit(self, node: ast.Node) -> Any:
        """:meta private:"""
        self._depth += 1
        res = super().visit(node)
        self._depth -= 1

        if self._depth == 0:
            res = self._ensure_q(res)

        return res

    def visit_Identifier(self, node: ast.Identifier) -> F:
        ":meta private:"
        resolved_field = self._validate_field(node.name)
        return F(resolved_field)

    def visit_Attribute(self, node: ast.Attribute) -> F:
        ":meta private:"
        owner = self.visit(node.owner)
        full_id = owner.name + "__" + node.attr
        resolved_field = self._validate_field(full_id)
        return F(resolved_field)

    def visit_Null(self, node: ast.Null) -> str:
        ":meta private:"
        raise NotImplementedError("Should not be reached")

    def visit_Integer(self, node: ast.Integer) -> Value:
        ":meta private:"
        return Value(node.py_val)

    def visit_Float(self, node: ast.Float) -> Value:
        ":meta private:"
        return Value(node.py_val)

    def visit_Boolean(self, node: ast.Boolean) -> Value:
        ":meta private:"
        return Value(node.py_val)

    def visit_String(self, node: ast.String) -> Value:
        ":meta private:"
        return Value(node.py_val)

    def visit_Date(self, node: ast.Date) -> Value:
        ":meta private:"
        try:
            return Value(node.py_val)
        except ValueError:
            raise core_ex.InvalidValueError(node.val, expected_type="Date")

    def visit_DateTime(self, node: ast.DateTime) -> Value:
        ":meta private:"
        try:
            return Value(node.py_val)
        except ValueError:
            raise core_ex.InvalidValueError(node.val, expected_type="DateTime")

    def visit_Time(self, node: ast.Time) -> Value:
        ":meta private:"
        try:
            return Value(node.py_val)
        except ValueError:
            raise core_ex.InvalidValueError(node.val, expected_type="Time")

    def visit_Duration(self, node: ast.Duration) -> Value:
        ":meta private:"
        return Value(node.py_val)

    def visit_GUID(self, node: ast.GUID) -> Value:
        ":meta private:"
        return Value(node.py_val)

    def visit_List(self, node: ast.List) -> list:
        ":meta private:"
        return [self.visit(n) for n in node.val]

    def visit_Add(self, node: ast.Add) -> Callable[[Any, Any], Any]:
        ":meta private:"
        return operator.add

    def visit_Sub(self, node: ast.Sub) -> Callable[[Any, Any], Any]:
        ":meta private:"
        return operator.sub

    def visit_Mult(self, node: ast.Mult) -> Callable[[Any, Any], Any]:
        ":meta private:"
        return operator.mul

    def visit_Div(self, node: ast.Div) -> Callable[[Any, Any], Any]:
        ":meta private:"
        return operator.truediv

    def visit_Mod(self, node: ast.Mod) -> Callable[[Any, Any], Any]:
        ":meta private:"
        return operator.mod

    def visit_BinOp(self, node: ast.BinOp) -> Any:
        ":meta private:"
        # Left or right can be an Identifier, in which case it needs to be
        # wrapped in F()
        left = self.visit(node.left)
        right = self.visit(node.right)
        op = self.visit(node.op)

        return op(left, right)

    def visit_Eq(self, node: ast.Eq) -> type[lookups.Lookup]:
        ":meta private:"
        return cast(type[lookups.Lookup], lookups.Exact)

    def visit_NotEq(self, node: ast.NotEq) -> type[lookups.Lookup]:
        ":meta private:"
        return cast(type[lookups.Lookup], NotEqual)

    def visit_Lt(self, node: ast.Lt) -> type[lookups.Lookup]:
        ":meta private:"
        return cast(type[lookups.Lookup], lookups.LessThan)

    def visit_LtE(self, node: ast.LtE) -> type[lookups.Lookup]:
        ":meta private:"
        return cast(type[lookups.Lookup], lookups.LessThanOrEqual)

    def visit_Gt(self, node: ast.Gt) -> type[lookups.Lookup]:
        ":meta private:"
        return cast(type[lookups.Lookup], lookups.GreaterThan)

    def visit_GtE(self, node: ast.GtE) -> type[lookups.Lookup]:
        ":meta private:"
        return cast(type[lookups.Lookup], lookups.GreaterThanOrEqual)

    def visit_In(self, node: ast.In) -> type[lookups.Lookup]:
        ":meta private:"
        return cast(type[lookups.Lookup], lookups.In)

    def visit_Compare(self, node: ast.Compare) -> lookups.Lookup:
        ":meta private:"
        lhs = self.visit(node.left)

        # Special case: comparison to NULL => isnull=True/False
        # Should not be wrapped with Value(True/False)
        # See: https://github.com/django/django/blob/0aacbdcf27b258387643b033352e99e6103abda8/django/db/models/lookups.py#L515
        if isinstance(node.right, ast.Null):
            if isinstance(node.comparator, ast.Eq):
                return lookups.IsNull(lhs, True)
            elif isinstance(node.comparator, ast.NotEq):
                return lookups.IsNull(lhs, False)
            else:
                raise core_ex.TypeMismatchError(
                    expected="Eq or NotEq for null comparison", actual=node.comparator.__class__.__name__
                )

        django_cls = self.visit(node.comparator)
        rhs = self.visit(node.right)

        return django_cls(lhs, rhs)

    def visit_And(self, node: ast.And) -> Callable[[Q, Q], Q]:
        ":meta private:"
        return operator.and_

    def visit_Or(self, node: ast.Or) -> Callable[[Q, Q], Q]:
        ":meta private:"
        return operator.or_

    def visit_BoolOp(self, node: ast.BoolOp) -> Q:
        ":meta private:"
        left = self.visit(node.left)
        right = self.visit(node.right)

        if isinstance(left, (F, Value)):
            raise core_ex.TypeMismatchError(expected="Q object", actual=str(left), context=node.op.__class__.__name__)
        if isinstance(right, (F, Value)):
            raise core_ex.TypeMismatchError(expected="Q object", actual=str(right), context=node.op.__class__.__name__)

        op = self.visit(node.op)

        return op(left, right)

    def visit_Not(self, node: ast.Not) -> Callable[[Q], Q]:
        ":meta private:"
        return operator.invert

    def visit_UnaryOp(self, node: ast.UnaryOp) -> Q:
        ":meta private:"
        mod = self.visit(node.op)
        val = self.visit(node.operand)

        # Can only apply `~` to Q objects:
        val = self._ensure_q(val)

        try:
            return mod(val)
        except TypeError:
            raise core_ex.TypeMismatchError(expected="Q object", actual=str(val), context=node.op.__class__.__name__)

    def visit_Call(self, node: ast.Call) -> Expression | Q:
        ":meta private:"

        func_name = node.func.full_name().replace(".", "__")

        try:
            q_gen = getattr(self, "djangofunc_" + func_name.lower())
        except AttributeError:
            raise core_ex.UnsupportedFunctionError(func_name)

        args = []
        kwargs = {}
        for arg in node.args:
            if isinstance(arg, ast.NamedParam):
                kwargs[arg.name.name] = arg.param
            else:
                args.append(arg)

        res = q_gen(*args, **kwargs)
        return res

    def visit_CollectionLambda(self, node: ast.CollectionLambda) -> Q:
        ":meta private:"
        # NOTE: The initial implementation translated to SQL's ANY/ALL keywords,
        # but those behave very differently from OData's any/all keywords!

        owner_path = self._attempt_keywordify(node.owner)
        if not owner_path:
            raise core_ex.TypeMismatchError(
                expected="Keyword-compatible expression", actual=str(node.owner), context="lambda_expression"
            )

        path_to_outerref, related_model = reverse_relationship(owner_path, self.root_model)
        subquery = related_model.objects.filter(Q(**{path_to_outerref: OuterRef("pk")}))
        # .values(related_field.remote_field.name)

        if node.lambda_:
            # For the lambda, we want to strip the identifier off, because
            # we will execute this as a subquery in the wanted model's context.
            subq_ast = utils.expression_relative_to_identifier(node.lambda_.identifier, node.lambda_.expression)
            subq_transformer = self.__class__(related_model)
            subquery_filter = subq_transformer.visit(subq_ast)
        else:
            subquery_filter = None

        if isinstance(node.operator, ast.Any):
            # If ANY item should match in the subquery, we can use EXISTS():
            if subquery_filter:
                subquery = subquery.filter(subquery_filter)
            return Exists(subquery)

        elif isinstance(node.operator, ast.All):
            # If ALL items in the collection must match, we invert the condition and use NOT EXISTS():
            if subquery_filter:
                subquery = subquery.filter(~subquery_filter)
            return Exists(subquery, negated=True)

        else:
            raise NotImplementedError()

    def djangofunc_contains(self, field: ast.Node, substr: ast.Node) -> lookups.Contains:
        ":meta private:"
        return self._substr_function(field, substr, lookups.Contains)

    def djangofunc_startswith(self, field: ast.Node, substr: ast.Node) -> lookups.StartsWith:
        ":meta private:"
        return self._substr_function(field, substr, lookups.StartsWith)

    def djangofunc_endswith(self, field: ast.Node, substr: ast.Node) -> lookups.EndsWith:
        ":meta private:"
        return self._substr_function(field, substr, lookups.EndsWith)

    def djangofunc_length(self, arg: ast.Node) -> functions.Length:
        ":meta private:"
        return functions.Length(self.visit(arg))

    def djangofunc_concat(self, *args: ast.Node) -> functions.Concat:
        ":meta private:"
        return functions.Concat(*[self.visit(arg) for arg in args])

    def djangofunc_indexof(self, first: ast.Node, second: ast.Node) -> functions.StrIndex:
        ":meta private:"
        # Subtract 1 because OData is 0-indexed while SQL is 1-indexed
        return functions.StrIndex(self.visit(first), self.visit(second)) - 1

    def djangofunc_substring(
        self, fullstr: ast.Node, index: ast.Node, nchars: ast.Node | None = None
    ) -> functions.Substr:
        ":meta private:"
        # Add 1 because OData is 0-indexed while SQL is 1-indexed
        return functions.Substr(
            self.visit(fullstr),
            self.visit(index) + 1,
            self.visit(nchars) if nchars else None,
        )

    def djangofunc_matchespattern(self, field: ast.Node, pattern: ast.Node) -> lookups.Regex:
        ":meta private:"
        return lookups.Regex(self.visit(field), self.visit(pattern))

    def djangofunc_tolower(self, field: ast.Node) -> functions.Lower:
        ":meta private:"
        return functions.Lower(self.visit(field))

    def djangofunc_toupper(self, field: ast.Node) -> functions.Upper:
        ":meta private:"
        return functions.Upper(self.visit(field))

    def djangofunc_trim(self, field: ast.Node) -> functions.Trim:
        ":meta private:"
        return functions.Trim(self.visit(field))

    def djangofunc_date(self, field: ast.Node) -> functions.TruncDate:
        ":meta private:"
        return functions.TruncDate(self.visit(field))

    def djangofunc_day(self, field: ast.Node) -> functions.ExtractDay:
        ":meta private:"
        return functions.ExtractDay(self.visit(field))

    def djangofunc_hour(self, field: ast.Node) -> functions.ExtractHour:
        ":meta private:"
        return functions.ExtractHour(self.visit(field))

    def djangofunc_minute(self, field: ast.Node) -> functions.ExtractMinute:
        ":meta private:"
        return functions.ExtractMinute(self.visit(field))

    def djangofunc_month(self, field: ast.Node) -> functions.ExtractMonth:
        ":meta private:"
        return functions.ExtractMonth(self.visit(field))

    def djangofunc_now(self) -> functions.Now:
        ":meta private:"
        return functions.Now()

    def djangofunc_second(self, field: ast.Node) -> functions.ExtractSecond:
        ":meta private:"
        return functions.ExtractSecond(self.visit(field))

    def djangofunc_time(self, field: ast.Node) -> functions.TruncTime:
        ":meta private:"
        return functions.TruncTime(self.visit(field))

    def djangofunc_year(self, field: ast.Node) -> functions.ExtractYear:
        ":meta private:"
        return functions.ExtractYear(self.visit(field))

    def djangofunc_ceiling(self, field: ast.Node) -> functions.Ceil:
        ":meta private:"
        return functions.Ceil(self.visit(field))

    def djangofunc_floor(self, field: ast.Node) -> functions.Floor:
        ":meta private:"
        return functions.Floor(self.visit(field))

    def djangofunc_round(self, field: ast.Node) -> functions.Round:
        ":meta private:"
        return functions.Round(self.visit(field))

    def _substr_function(self, field: ast.Node, substr: ast.Node, django_func: type[Expression]) -> Expression:
        ":meta private:"
        self._check_type(field, (ast.Identifier, ast.String, ast.Call), "field")
        self._check_type(substr, ast.String, "substring")

        return django_func(self.visit(field), self.visit(substr))

    def _check_type(self, value: Any, expected_type: type | tuple[type, ...], name: str) -> None:
        """Helper to replace typing.typecheck without depending on odata module."""
        if not isinstance(value, expected_type):
            expected_name = (
                expected_type.__name__ if isinstance(expected_type, type) else [t.__name__ for t in expected_type]
            )
            raise core_ex.TypeMismatchError(expected=expected_name, actual=type(value).__name__, context=name)

    def _fix_uuid(self, node: Any) -> Any:
        # Workaround for Django <4 'Value is not a valid UUID':
        if isinstance(node, Value) and isinstance(node.value, UUID):
            return node.value

        if isinstance(node, list):
            return [self._fix_uuid(i) for i in node]

        return node

    def _ensure_q(self, node: Any) -> Q:
        """
        Turn a given Django `Lookup`, `Expression` or `Function` into a `Q` object.
        In Django >= 4, expressions can be directly used in Q objects.
        """
        if isinstance(node, (Q, Exists)):
            return node
        return Q(node)

    def _attempt_keywordify(self, node: Any) -> str | None:
        """
        Try to turn ``node`` into a keyword argument that can be used in a Django
        ``Q`` object. E.g. a ``contains(name, 'something')`` node should resolve
        to the keyword ``name__contains``.

        :meta private:
        """
        # A literal can not be expressed as a keyword.
        if isinstance(node, (ast._Literal, Value)):
            return None

        # If an AST Node was passed, visit it to get something Django related:
        if isinstance(node, ast.Node):
            res = self.visit(node)
        else:
            res = node

        # If `res` is already wrapped in a `Q` object, we need to unwrap it first.
        # This is the case with expressions that are filterable by themselves,
        # such as `contains(a, b)`.
        if isinstance(res, Q) and isinstance(res.children[0], Expression):
            res = res.children[0]

        # An `F` expression is a field or expression known to Django, and can
        # be used as a keyword.
        if isinstance(res, F):
            return res.name

        # Field lookups are also easily expressed as keywords.
        if (
            hasattr(res, "lookup_name")
            and hasattr(res, "lhs")
            and hasattr(res.lhs, "name")
            # Expressions with a `rhs` have parameters and should be handled
            # as function calls:
            and not getattr(res, "rhs", False)
        ):
            return res.lhs.name + "__" + res.lookup_name

        # Lookups with parameters need to be wrapped in a `CASE WHEN` expression
        if isinstance(res, lookups.Lookup):
            identity = self._gen_annotation_name(res)
            res = Case(When(res, then=True), default=False)
            self.queryset_annotations[identity] = res
            return identity

        # For more complicated expressions, we can add them to the query as a
        # QuerySet annotation. This annotation is then valid as a keyword:
        if isinstance(res, Expression):
            identity = self._gen_annotation_name(res)
            self.queryset_annotations[identity] = res
            return identity

        return None

    def _gen_annotation_name(self, expr: Expression) -> str:
        ":meta private:"
        if hasattr(expr, "name"):
            return str(expr.name)
        elif hasattr(expr, "value"):
            return str(expr.value)

        func_name = expr.__class__.__name__

        try:
            args = expr.get_source_expressions()
        except AttributeError:
            args = []

        args_str = [self._gen_annotation_name(a) for a in args]

        return "_".join([func_name] + args_str).replace(" ", "_").replace(",", "").replace(":", "_").lower()

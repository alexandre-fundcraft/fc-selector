import operator
import re
from typing import Any

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
from fc_selector.core.utils import get_base_field, is_private_field, odata_path_to_django
from fc_selector.django.utils import get_field_safe, resolve_field_alias

# We still use utils from parsers to manipulate AST nodes (should be moved to core later)
from fc_selector.protocols.odata.parsers.filter import utils

from .django_q_ext import NotEqual
from .utils import reverse_relationship

# Security: Maximum regex pattern length to prevent ReDoS attacks
MAX_REGEX_PATTERN_LENGTH = 256

# What each operator token visits to: a Python operator for arithmetic and
# boolean ops, a Django lookup class for comparisons.
_OPERATOR_TOKENS: dict[type, Any] = {
    # Arithmetic
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    # Comparison
    ast.Eq: lookups.Exact,
    ast.NotEq: NotEqual,
    ast.Lt: lookups.LessThan,
    ast.LtE: lookups.LessThanOrEqual,
    ast.Gt: lookups.GreaterThan,
    ast.GtE: lookups.GreaterThanOrEqual,
    ast.In: lookups.In,
    # Boolean
    ast.And: operator.and_,
    ast.Or: operator.or_,
    ast.Not: operator.invert,
}


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

    def _validate_field(self, field_name: str) -> str:
        """Validate a field for security and return it with aliases resolved.

        ``allowed_fields`` holds API-facing names, so it is checked before alias
        resolution. When it is set, the field may be a queryset annotation rather
        than a model field, so no existence check is done. Paths ("a__b") are left
        to Django's join machinery.
        """
        if is_private_field(field_name):
            raise core_ex.InvalidFieldError(
                field_name, self.root_model.__name__, reason="access to private fields is not allowed"
            )

        if self.allowed_fields is not None:
            if get_base_field(field_name) not in self.allowed_fields:
                raise core_ex.InvalidFieldError(
                    field_name, self.root_model.__name__, reason="field is not in allowed fields list"
                )
            return resolve_field_alias(field_name, self.field_aliases)

        resolved_field = resolve_field_alias(field_name, self.field_aliases)
        if "__" not in resolved_field and get_field_safe(self.root_model, resolved_field) is None:
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
            res = AstToDjangoQVisitor._ensure_q(res)

        return res

    def generic_visit(self, node: ast.Node) -> Any:
        """Operator tokens and plain literals need no visitor of their own.

        ``Null`` and ``List`` keep explicit visitors because they are not plain
        values.
        """
        token = _OPERATOR_TOKENS.get(type(node))
        if token is not None:
            return token

        if isinstance(node, ast._Literal):
            try:
                return Value(node.py_val)
            except ValueError as exc:
                # Date/DateTime/Time literals only parse when py_val is read
                raw = getattr(node, "val", node)
                raise core_ex.InvalidValueError(raw, expected_type=type(node).__name__) from exc

        return super().generic_visit(node)

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

    @staticmethod
    def visit_Null(node: ast.Null) -> str:
        ":meta private:"
        raise NotImplementedError("Should not be reached")

    def visit_List(self, node: ast.List) -> list:
        ":meta private:"
        return [self.visit(n) for n in node.val]

    def visit_BinOp(self, node: ast.BinOp) -> Any:
        ":meta private:"
        # Left or right can be an Identifier, in which case it needs to be
        # wrapped in F()
        left = self.visit(node.left)
        right = self.visit(node.right)
        op = self.visit(node.op)

        return op(left, right)

    def visit_Compare(self, node: ast.Compare) -> lookups.Lookup:
        ":meta private:"
        lhs = self.visit(node.left)

        # Special case: comparison to NULL => isnull=True/False
        # Should not be wrapped with Value(True/False)
        # See: https://github.com/django/django/blob/0aacbdcf27b258387643b033352e99e6103abda8/django/db/models/lookups.py#L515
        if isinstance(node.right, ast.Null):
            if isinstance(node.comparator, ast.Eq):
                return lookups.IsNull(lhs, True)
            if isinstance(node.comparator, ast.NotEq):
                return lookups.IsNull(lhs, False)
            raise core_ex.TypeMismatchError(
                expected="Eq or NotEq for null comparison", actual=node.comparator.__class__.__name__
            )

        django_cls = self.visit(node.comparator)
        rhs = self.visit(node.right)

        return django_cls(lhs, rhs)

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

    def visit_UnaryOp(self, node: ast.UnaryOp) -> Q:
        ":meta private:"
        mod = self.visit(node.op)
        val = self.visit(node.operand)

        # Can only apply `~` to Q objects:
        val = AstToDjangoQVisitor._ensure_q(val)

        try:
            return mod(val)
        except TypeError as exc:
            raise core_ex.TypeMismatchError(
                expected="Q object", actual=str(val), context=node.op.__class__.__name__
            ) from exc

    def visit_Call(self, node: ast.Call) -> Expression | Q:
        ":meta private:"

        func_name = odata_path_to_django(node.func.full_name())

        try:
            q_gen = getattr(self, "djangofunc_" + func_name.lower())
        except AttributeError as exc:
            raise core_ex.UnsupportedFunctionError(func_name) from exc

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

        if isinstance(node.operator, ast.All):
            # If ALL items in the collection must match, we invert the condition and use NOT EXISTS():
            if subquery_filter is not None:
                # Negate the filter condition for ALL semantics
                subquery = subquery.filter(~subquery_filter)
            return Exists(subquery, negated=True)

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
        visited_pattern = self.visit(pattern)

        # Extract pattern string for validation
        pattern_str = visited_pattern.value if hasattr(visited_pattern, "value") else str(visited_pattern)

        # Security: Validate pattern length to prevent ReDoS
        if len(pattern_str) > MAX_REGEX_PATTERN_LENGTH:
            raise core_ex.InvalidValueError(
                pattern_str[:50] + "...",
                expected_type="regex pattern",
                context=f"pattern too long (max {MAX_REGEX_PATTERN_LENGTH} chars)",
            )

        # Security: Validate regex compiles (catches syntax errors and some dangerous patterns)
        try:
            re.compile(pattern_str)
        except re.error as e:
            raise core_ex.InvalidValueError(
                pattern_str[:100],
                expected_type="valid regex pattern",
                context=str(e),
            )

        return lookups.Regex(self.visit(field), visited_pattern)

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

    @staticmethod
    def djangofunc_now() -> functions.Now:
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
        AstToDjangoQVisitor._check_type(field, (ast.Identifier, ast.String, ast.Call), "field")
        AstToDjangoQVisitor._check_type(substr, ast.String, "substring")

        return django_func(self.visit(field), self.visit(substr))

    @staticmethod
    def _check_type(value: Any, expected_type: type | tuple[type, ...], name: str) -> None:
        """Helper to replace typing.typecheck without depending on odata module."""
        if not isinstance(value, expected_type):
            expected_name = (
                expected_type.__name__ if isinstance(expected_type, type) else [t.__name__ for t in expected_type]
            )
            raise core_ex.TypeMismatchError(expected=expected_name, actual=type(value).__name__, context=name)

    @staticmethod
    def _ensure_q(node: Any) -> Q:
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
            return str(res.name)

        # Field lookups are also easily expressed as keywords.
        if (
            hasattr(res, "lookup_name")
            and hasattr(res, "lhs")
            and hasattr(res.lhs, "name")
            # Expressions with a `rhs` have parameters and should be handled
            # as function calls:
            and not getattr(res, "rhs", False)
        ):
            return str(res.lhs.name) + "__" + str(res.lookup_name)

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
            base = str(expr.name)
        elif hasattr(expr, "value"):
            base = str(expr.value)
        else:
            base = expr.__class__.__name__

            try:
                args = expr.get_source_expressions()
            except AttributeError:
                args = []

            args_str = [self._gen_annotation_name(a) for a in args]
            base = "_".join([base] + args_str)

        # Security: Strict sanitization - only allow safe characters for SQL identifiers
        sanitized = re.sub(r"[^a-z0-9_]", "_", base.lower())
        sanitized = re.sub(r"_+", "_", sanitized)  # Collapse multiple underscores
        sanitized = sanitized.strip("_")
        sanitized = sanitized[:63]  # PostgreSQL identifier limit

        # Ensure valid identifier (starts with letter or underscore)
        if sanitized and sanitized[0].isdigit():
            sanitized = f"expr_{sanitized}"

        return sanitized or "expr_unknown"

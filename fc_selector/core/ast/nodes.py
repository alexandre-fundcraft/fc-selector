"""
AST Node Definitions for OData Query Language.

This module defines the Abstract Syntax Tree (AST) node types used to represent
parsed OData query expressions. These nodes are framework-agnostic and can be
transformed into framework-specific query objects using the visitor pattern.

Original Code: https://github.com/gorilla-co/odata-query
License: MIT
Authors: Original odata-query authors
Modified by: Alexandre Busquets (django-odata)

Modifications:
- Added comprehensive docstrings
- Maintained MIT license and original credits
"""

import datetime as dt
import re
from dataclasses import dataclass, field
from uuid import UUID

DURATION_PATTERN = re.compile(r"([+-])?P(\d+Y)?(\d+M)?(\d+D)?(?:T(\d+H)?(\d+M)?(\d+(?:\.\d+)?S)?)?")


@dataclass(frozen=True)
class Node:
    """
    Base class for all AST nodes.

    All AST nodes are immutable (frozen=True) to ensure thread safety
    and allow caching of parsed queries.
    """

    pass


@dataclass(frozen=True)
class Identifier(Node):
    """
    Represents a field or variable identifier.

    Examples:
        - "name" → Identifier(name="name", namespace=())
        - "geo.distance" → Identifier(name="distance", namespace=("geo",))

    Attributes:
        name: The identifier name
        namespace: Optional namespace prefix (for namespaced functions)
    """

    name: str
    namespace: tuple[str, ...] = field(default_factory=tuple)

    def full_name(self):
        """Return the full qualified name including namespace."""
        return ".".join(self.namespace + (self.name,))


@dataclass(frozen=True)
class Attribute(Node):
    """
    Represents navigation property access (e.g., author.name).

    In OData, properties are accessed with "/" but represented as Attribute nodes:
    - "author/user/first_name" → Attribute(Attribute(Identifier('author'), 'user'), 'first_name')

    Attributes:
        owner: The object being accessed (Identifier or another Attribute)
        attr: The attribute name
    """

    owner: Node
    attr: str


###############################################################################
# Literals
###############################################################################
@dataclass(frozen=True)
class _Literal(Node):
    """Base class for all literal value nodes."""

    pass

    @property
    def py_val(self):
        """Convert OData literal to Python value."""
        raise NotImplementedError()


@dataclass(frozen=True)
class Null(_Literal):
    """Represents the OData null literal."""

    @property
    def py_val(self) -> None:
        return None


@dataclass(frozen=True)
class Integer(_Literal):
    """
    Represents an integer literal.

    Examples:
        - "42" → Integer(val="42") → py_val = 42
        - "-10" → Integer(val="-10") → py_val = -10
    """

    val: str

    @property
    def py_val(self) -> int:
        return int(self.val)


@dataclass(frozen=True)
class Float(_Literal):
    """
    Represents a floating-point literal.

    Examples:
        - "3.14" → Float(val="3.14") → py_val = 3.14
        - "-2.5" → Float(val="-2.5") → py_val = -2.5
    """

    val: str

    @property
    def py_val(self) -> float:
        return float(self.val)


@dataclass(frozen=True)
class Boolean(_Literal):
    """
    Represents a boolean literal.

    Examples:
        - "true" → Boolean(val="true") → py_val = True
        - "false" → Boolean(val="false") → py_val = False
    """

    val: str

    @property
    def py_val(self) -> bool:
        return self.val.lower() == "true"


@dataclass(frozen=True)
class String(_Literal):
    """
    Represents a string literal.

    Examples:
        - "'hello'" → String(val="'hello'") → py_val = "'hello'"
        - "'John Doe'" → String(val="'John Doe'") → py_val = "'John Doe'"

    Note: The quotes are preserved in val for proper escaping handling.
    """

    val: str

    @property
    def py_val(self) -> str:
        return self.val


@dataclass(frozen=True)
class Date(_Literal):
    """
    Represents a date literal (ISO 8601 format).

    Examples:
        - "2023-01-15" → Date(val="2023-01-15") → py_val = date(2023, 1, 15)
    """

    val: str

    @property
    def py_val(self) -> dt.date:
        return dt.date.fromisoformat(self.val)


@dataclass(frozen=True)
class Time(_Literal):
    """
    Represents a time literal (ISO 8601 format).

    Examples:
        - "14:30:00" → Time(val="14:30:00") → py_val = time(14, 30, 0)
    """

    val: str

    @property
    def py_val(self) -> dt.time:
        return dt.time.fromisoformat(self.val)


@dataclass(frozen=True)
class DateTime(_Literal):
    """
    Represents a datetime literal (ISO 8601 format).

    Examples:
        - "2023-01-15T14:30:00Z" → DateTime(val="2023-01-15T14:30:00Z")
          → py_val = datetime(2023, 1, 15, 14, 30, 0, tzinfo=timezone.utc)
    """

    val: str

    @property
    def py_val(self) -> dt.datetime:
        return dt.datetime.fromisoformat(self.val)


@dataclass(frozen=True)
class Duration(_Literal):
    """
    Represents a duration literal (ISO 8601 duration format).

    Examples:
        - "P1D" → 1 day
        - "PT2H30M" → 2 hours 30 minutes
        - "P1Y2M3DT4H5M6S" → 1 year, 2 months, 3 days, 4 hours, 5 minutes, 6 seconds

    Note: Year and month conversions are approximate:
        - 1 year ≈ 365.25 days
        - 1 month ≈ 30.44 days
    """

    val: str

    @property
    def py_val(self) -> dt.timedelta:
        sign, years, months, days, hours, minutes, seconds = self.unpack()

        # Initialize days to 0 if None
        num_days = float(days or 0)

        # Approximate conversion, adjust as necessary for more precision
        num_days += float(years or 0) * 365.25  # Average including leap years
        num_days += float(months or 0) * 30.44  # Average month length

        delta = dt.timedelta(
            days=num_days,
            hours=float(hours or 0),
            minutes=float(minutes or 0),
            seconds=float(seconds or 0),
        )
        if sign and sign == "-":
            delta = -1 * delta
        return delta

    def unpack(
        self,
    ) -> tuple[
        str | None,
        str | None,
        str | None,
        str | None,
        str | None,
        str | None,
        str | None,
    ]:
        """
        Unpack the duration into its components.

        Returns:
            Tuple of (sign, years, months, days, hours, minutes, seconds)
        """

        match = DURATION_PATTERN.fullmatch(self.val)
        if not match:
            raise ValueError(f"Could not unpack Duration with value {self.val}")

        sign, years, months, days, hours, minutes, seconds = match.groups()

        _years = years[:-1] if years else None
        _months = months[:-1] if months else None
        _days = days[:-1] if days else None
        _hours = hours[:-1] if hours else None
        _minutes = minutes[:-1] if minutes else None
        _seconds = seconds[:-1] if seconds else None

        return sign, _years, _months, _days, _hours, _minutes, _seconds


@dataclass(frozen=True)
class GUID(_Literal):
    """
    Represents a GUID/UUID literal.

    Examples:
        - "guid'12345678-1234-1234-1234-123456789abc'"
          → GUID(val="12345678-1234-1234-1234-123456789abc")
          → py_val = UUID('12345678-1234-1234-1234-123456789abc')
    """

    val: str

    @property
    def py_val(self) -> UUID:
        return UUID(self.val)


@dataclass(frozen=True)
class List(_Literal):
    """
    Represents a list of literals.

    Examples:
        - "[1, 2, 3]" → List(val=[Integer("1"), Integer("2"), Integer("3")])
        - "['a', 'b']" → List(val=[String("'a'"), String("'b'")])

    Used with the "in" operator:
        - "status in ('active', 'pending')"
    """

    val: list[_Literal]

    @property
    def py_val(self) -> list:
        return [v.py_val for v in self.val]


###############################################################################
# Arithmetic Operators
###############################################################################
@dataclass(frozen=True)
class _BinOpToken(Node):
    """Base class for binary operator tokens."""

    pass


@dataclass(frozen=True)
class Add(_BinOpToken):
    """Addition operator: a add b"""

    pass


@dataclass(frozen=True)
class Sub(_BinOpToken):
    """Subtraction operator: a sub b"""

    pass


@dataclass(frozen=True)
class Mult(_BinOpToken):
    """Multiplication operator: a mul b"""

    pass


@dataclass(frozen=True)
class Div(_BinOpToken):
    """Division operator: a div b"""

    pass


@dataclass(frozen=True)
class Mod(_BinOpToken):
    """Modulo operator: a mod b"""

    pass


@dataclass(frozen=True)
class BinOp(Node):
    """
    Represents a binary arithmetic operation.

    Examples:
        - "price add 10" → BinOp(op=Add(), left=Identifier('price'), right=Integer('10'))
        - "quantity mul 2" → BinOp(op=Mult(), left=Identifier('quantity'), right=Integer('2'))

    Attributes:
        op: The operator (Add, Sub, Mult, Div, Mod)
        left: Left operand
        right: Right operand
    """

    op: _BinOpToken
    left: Node
    right: Node


###############################################################################
# Comparison Operators
###############################################################################
@dataclass(frozen=True)
class _Comparator(Node):
    """Base class for comparison operator tokens."""

    pass


@dataclass(frozen=True)
class Eq(_Comparator):
    """Equality: a eq b"""

    pass


@dataclass(frozen=True)
class NotEq(_Comparator):
    """Inequality: a ne b"""

    pass


@dataclass(frozen=True)
class Lt(_Comparator):
    """Less than: a lt b"""

    pass


@dataclass(frozen=True)
class LtE(_Comparator):
    """Less than or equal: a le b"""

    pass


@dataclass(frozen=True)
class Gt(_Comparator):
    """Greater than: a gt b"""

    pass


@dataclass(frozen=True)
class GtE(_Comparator):
    """Greater than or equal: a ge b"""

    pass


@dataclass(frozen=True)
class In(_Comparator):
    """In operator: a in [b, c, d]"""

    pass


@dataclass(frozen=True)
class Compare(Node):
    """
    Represents a comparison expression.

    Examples:
        - "name eq 'John'" → Compare(comparator=Eq(), left=Identifier('name'), right=String("'John'"))
        - "rating gt 4.0" → Compare(comparator=Gt(), left=Identifier('rating'), right=Float('4.0'))
        - "status in ('active', 'pending')" → Compare(comparator=In(), left=Identifier('status'), right=List([...]))

    Attributes:
        comparator: The comparison operator (Eq, NotEq, Lt, LtE, Gt, GtE, In)
        left: Left operand (usually an Identifier or Attribute)
        right: Right operand (usually a Literal)
    """

    comparator: _Comparator
    left: Node
    right: Node


###############################################################################
# Boolean Operators
###############################################################################
@dataclass(frozen=True)
class _BoolOpToken(Node):
    """Base class for boolean operator tokens."""

    pass


@dataclass(frozen=True)
class And(_BoolOpToken):
    """Logical AND: a and b"""

    pass


@dataclass(frozen=True)
class Or(_BoolOpToken):
    """Logical OR: a or b"""

    pass


@dataclass(frozen=True)
class BoolOp(Node):
    """
    Represents a boolean operation (AND/OR).

    Examples:
        - "name eq 'John' and age gt 30"
          → BoolOp(op=And(), left=Compare(...), right=Compare(...))

        - "status eq 'active' or status eq 'pending'"
          → BoolOp(op=Or(), left=Compare(...), right=Compare(...))

    Boolean operations are left-associative and can be nested:
        - "a and b and c" → BoolOp(And, BoolOp(And, a, b), c)

    Attributes:
        op: The operator (And, Or)
        left: Left boolean expression
        right: Right boolean expression
    """

    op: _BoolOpToken
    left: Node
    right: Node


###############################################################################
# Unary Operators
###############################################################################
@dataclass(frozen=True)
class _UnaryOpToken(Node):
    """Base class for unary operator tokens."""

    pass


@dataclass(frozen=True)
class Not(_UnaryOpToken):
    """Logical NOT: not expression"""

    pass


@dataclass(frozen=True)
class USub(_UnaryOpToken):
    """Unary negation: -value"""

    pass


@dataclass(frozen=True)
class UnaryOp(Node):
    """
    Represents a unary operation.

    Examples:
        - "not (status eq 'inactive')" → UnaryOp(op=Not(), operand=Compare(...))
        - "-quantity" → UnaryOp(op=USub(), operand=Identifier('quantity'))

    Attributes:
        op: The operator (Not, USub)
        operand: The expression to apply the operator to
    """

    op: _UnaryOpToken
    operand: Node


###############################################################################
# Function Calls
###############################################################################
@dataclass(frozen=True)
class NamedParam(Node):
    """
    Represents a named parameter in a function call.

    Examples:
        - "func(param=value)" → NamedParam(name=Identifier('param'), param=value)

    Attributes:
        name: Parameter name
        param: Parameter value
    """

    name: Identifier
    param: Node


@dataclass(frozen=True)
class Call(Node):
    """
    Represents a function call.

    Examples:
        - "contains(name, 'John')"
          → Call(func=Identifier('contains'), args=[Identifier('name'), String("'John'")])

        - "year(created_at) eq 2023"
          → Compare(comparator=Eq(),
                    left=Call(func=Identifier('year'), args=[Identifier('created_at')]),
                    right=Integer('2023'))

    OData supports many built-in functions:
        - String: contains, startswith, endswith, length, indexof, substring, tolower, toupper, trim, concat
        - Date/Time: year, month, day, hour, minute, second, date, time, now
        - Math: round, floor, ceiling
        - Geo: geo.distance, geo.intersects, geo.length

    Attributes:
        func: Function identifier (may include namespace like "geo.distance")
        args: List of arguments (may include NamedParam for named arguments)
    """

    func: Identifier
    args: list[Node]


###############################################################################
# Collection Lambda Expressions
###############################################################################
@dataclass(frozen=True)
class _CollectionOperator(Node):
    """Base class for collection operator tokens."""

    pass


@dataclass(frozen=True)
class Any(_CollectionOperator):
    """
    Any operator: collection/any(variable: condition)

    Returns true if any item in the collection satisfies the condition.

    Examples:
        - "comments/any(c: c/rating gt 4)"
          → At least one comment has rating > 4

        - "tags/any()" → Collection is not empty
    """

    pass


@dataclass(frozen=True)
class All(_CollectionOperator):
    """
    All operator: collection/all(variable: condition)

    Returns true if all items in the collection satisfy the condition.

    Examples:
        - "comments/all(c: c/status eq 'approved')"
          → All comments have status = 'approved'
    """

    pass


@dataclass(frozen=True)
class Lambda(Node):
    """
    Represents the lambda part of a collection operation.

    Examples:
        - "c: c/rating gt 4" → Lambda(identifier=Identifier('c'),
                                      expression=Compare(...))

    Attributes:
        identifier: The lambda variable name
        expression: The filter expression using the variable
    """

    identifier: Identifier
    expression: Node


@dataclass(frozen=True)
class CollectionLambda(Node):
    """
    Represents a collection lambda expression (any/all).

    Examples:
        - "comments/any(c: c/rating gt 4)"
          → CollectionLambda(
              owner=Identifier('comments'),
              operator=Any(),
              lambda_=Lambda(identifier=Identifier('c'),
                           expression=Compare(comparator=Gt(),
                                            left=Attribute(Identifier('c'), 'rating'),
                                            right=Float('4')))
          )

        - "tags/any()" → CollectionLambda(owner=Identifier('tags'), operator=Any(), lambda_=None)

    Implementation in Django:
        - any() → Exists(subquery.filter(condition))
        - all() → ~Exists(subquery.filter(~condition))

    Attributes:
        owner: The collection being queried
        operator: Any or All
        lambda_: Optional lambda expression (None means just check if collection is non-empty)
    """

    owner: Node
    operator: _CollectionOperator
    lambda_: Lambda | None

# django_odata/core - Framework-Agnostic OData Layer

**Total**: 3,823 lines of Python code distributed across 7 submodules.

This package contains all the central OData logic that **does not depend on Django or any other framework**. It can be reused in other contexts (Flask, FastAPI, standalone, etc.).

---

## Table of Contents

1. [General Structure](#general-structure)
2. [Submodules](#submodules)
   - [AST (Abstract Syntax Tree)](#1-ast-abstract-syntax-tree)
   - [Parser](#2-parser-lexerparser-odata)
   - [Rewrite](#3-rewrite-ast-transformers)
   - [Query](#4-query-odata-query-models)
   - [Filter](#5-filter-filter-engine)
   - [DTOs](#6-dtos-data-transfer-objects)
   - [Selector](#7-selector-base-selector)
   - [Utils](#8-utils)
3. [Architecture Diagram](#architecture-diagram)
4. [Data Flow](#data-flow)
5. [Usage Examples](#usage-examples)

---

## General Structure

```
django_odata/core/
├── __init__.py                    # Entry point: parse_odata_query, get_filter_engine
│
├── ast/                           # ✅ Copied from odata-query (1,150 lines)
│   ├── nodes.py (729 lines)       # 40+ AST node types
│   ├── visitor.py (266 lines)     # NodeVisitor, NodeTransformer
│   └── __init__.py (155 lines)    # Exports
│
├── parser/                        # ✅ Copied from odata-query (921 lines)
│   ├── grammar.py (721 lines)     # ODataLexer, ODataParser (SLY)
│   ├── exceptions.py (152 lines)  # OData exceptions
│   └── __init__.py (48 lines)     # Exports
│
├── rewrite.py (90 lines)          # ✅ Copied from odata-query - AST transformers
├── typing.py (134 lines)          # ✅ Copied from odata-query - Type inference
├── utils.py (35 lines)            # ✅ Copied from odata-query - AST utils
│
├── query/                         # 📦 Original code (475 lines)
│   ├── models.py (137 lines)      # ODataQuery, ExpandItem, OrderByItem
│   ├── parser.py (232 lines)      # parse_odata_query()
│   ├── validators.py (94 lines)   # Query validators
│   └── __init__.py (14 lines)     # Exports
│
├── filter/                        # 📦 Original code (327 lines)
│   ├── engine.py (151 lines)      # Generic FilterEngine
│   ├── operators.py (131 lines)   # Filter operators
│   ├── exceptions.py (28 lines)   # Filter exceptions
│   └── __init__.py (17 lines)     # Exports
│
├── dtos/                          # 📦 Original code (454 lines)
│   ├── base.py (290 lines)        # Base DTO classes
│   ├── converter.py (156 lines)   # Model ↔ DTO converters
│   └── __init__.py (8 lines)      # Exports
│
├── selector/                      # 📦 Original code (222 lines)
│   ├── base.py (209 lines)        # BaseSelector protocol
│   └── __init__.py (13 lines)     # Exports
│
├── intent/                        # 📦 Original - Protocol-Agnostic Query Intent
│   ├── models.py                  # QueryIntent, FilterIntent, SelectIntent, etc.
│   ├── converters.py              # ODataQuery ↔ QueryIntent converters
│   └── __init__.py                # Exports
│
└── filters/                       # 📦 Original - Type-Safe Fluent API
    ├── fields.py                  # Field("name").eq("John")
    ├── expressions.py             # Expression wrapper with & | ~ operators
    ├── expand.py                  # Expand("author").select("name").top(5)
    ├── orderby.py                 # OrderBy("created_at").desc()
    └── __init__.py                # Exports: Field, Expand, OrderBy, Expression
```

**Legend:**
- ✅ = Copied from [odata-query](https://github.com/gorilla-co/odata-query) (MIT License)
- 📦 = Our original code

---

## Submodules

### 1. AST (Abstract Syntax Tree)

**Source**: Copied from `odata-query`
**Total**: 1,150 lines
**Purpose**: Represent OData expressions as immutable node trees.

#### 1.1 `ast/nodes.py` (729 lines) - The largest file

Defines 40+ AST node types with `@dataclass(frozen=True)`:

**Literals:**
```python
@dataclass(frozen=True)
class String(_Literal):
    val: str
    py_val: str

@dataclass(frozen=True)
class Integer(_Literal):
    val: str
    py_val: int

# Also: Float, Boolean, Date, DateTime, Duration, Null
```

**Comparators:**
```python
@dataclass(frozen=True)
class Eq(_Comparator):
    """Equality (eq)"""

# Also: NotEq, Lt, LtE, Gt, GtE
```

**Expressions:**
```python
@dataclass(frozen=True)
class Compare(Node):
    """name eq 'John'"""
    comparator: _Comparator  # Eq, NotEq, etc.
    left: Node              # Identifier('name')
    right: Node             # String('John')

@dataclass(frozen=True)
class BoolOp(Node):
    """name eq 'John' and age gt 30"""
    op: _BoolOperator        # And, Or
    values: List[Node]      # [Compare(...), Compare(...)]

@dataclass(frozen=True)
class Call(Node):
    """contains(name, 'John')"""
    func: Identifier         # Identifier('contains')
    args: List[Node]        # [Identifier('name'), String('John')]
```

**Lambda Expressions:**
```python
@dataclass(frozen=True)
class CollectionLambda(Node):
    """comments/any(c: c/rating gt 4)"""
    collection: Node        # Attribute('comments')
    expression: Node        # Compare(...)
    iterator_variable_name: str  # 'c'
```

**Identifiers:**
```python
@dataclass(frozen=True)
class Identifier(Node):
    """name"""
    name: str
    namespace: Tuple[str, ...] = ()

@dataclass(frozen=True)
class Attribute(Node):
    """author/name"""
    owner: Node  # Identifier('author')
    attr: str     # 'name'
```

#### 1.2 `ast/visitor.py` (266 lines)

Implementation of the **Visitor Pattern** (PEP 544):

```python
class NodeVisitor:
    """Base class for traversing AST."""

    def visit(self, node: nodes.Node) -> Any:
        """Calls the appropriate visit_<NodeType> method."""
        method = "visit_" + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node: nodes.Node) -> Any:
        """Fallback for nodes without a visitor."""
        return node

class NodeTransformer(NodeVisitor):
    """Visitor that allows modifying nodes."""

    def generic_visit(self, node: nodes.Node) -> nodes.Node:
        """Recursively visits and returns transformed node."""
        # Traverse and transform children
        # Return new node with transformed children
```

**Usage example:**
```python
class MyVisitor(NodeVisitor):
    def visit_Compare(self, node):
        print(f"Found comparison: {node.left} {node.comparator} {node.right}")
        return node

visitor = MyVisitor()
visitor.visit(ast_node)
```

---

### 2. Parser (Lexer/Parser OData)

**Source**: Copied from `odata-query`
**Total**: 921 lines
**Purpose**: Parse OData expressions to AST using SLY (Sly Lex-Yacc).

#### 2.1 `parser/grammar.py` (721 lines) - The second largest file

**ODataLexer** - Tokenization:
```python
class ODataLexer(Lexer):
    tokens = {
        # Identifiers and literals
        IDENTIFIER, STRING, INTEGER, FLOAT,

        # Comparators
        EQ, NE, LT, LE, GT, GE,

        # Logical operators
        AND, OR, NOT,

        # Functions
        CONTAINS, STARTSWITH, ENDSWITH, TOLOWER, TOUPPER,
        YEAR, MONTH, DAY, HOUR, MINUTE, SECOND,

        # Lambda
        ANY, ALL,

        # Geographic (to clean up later)
        GEO_DISTANCE, GEO_INTERSECTS,

        # Other
        LPAREN, RPAREN, COMMA, SLASH,
    }

    # Tokenization rules
    @_(r'[a-zA-Z_][a-zA-Z0-9_]*')
    def IDENTIFIER(self, t):
        # Converts keywords (eq, and, contains, etc.)
        t.type = self.keywords.get(t.value, 'IDENTIFIER')
        return t

    @_(r"'([^'\\\\]|\\\\.)*'")
    def STRING(self, t):
        t.value = t.value[1:-1]  # Remove quotes
        return t
```

**ODataParser** - Parsing to AST:
```python
class ODataParser(Parser):
    tokens = ODataLexer.tokens

    # Grammar
    @_('bool_expr')
    def filter_expr(self, p):
        return p.bool_expr

    @_('comparison_expr')
    def bool_expr(self, p):
        return p.comparison_expr

    @_('bool_expr AND comparison_expr')
    def bool_expr(self, p):
        return ast.BoolOp(ast.And(), [p.bool_expr, p.comparison_expr])

    @_('value EQ value')
    def comparison_expr(self, p):
        return ast.Compare(ast.Eq(), p.value0, p.value1)

    @_('CONTAINS LPAREN value COMMA value RPAREN')
    def function_call(self, p):
        return ast.Call(
            func=ast.Identifier('contains'),
            args=[p.value0, p.value1]
        )

    # Lambda expressions
    @_('attribute SLASH ANY LPAREN IDENTIFIER COLON bool_expr RPAREN')
    def lambda_any(self, p):
        return ast.CollectionLambda(
            collection=p.attribute,
            expression=p.bool_expr,
            iterator_variable_name=p.IDENTIFIER
        )
```

**Supported functions:**
- **String**: contains, startswith, endswith, tolower, toupper, trim, length, concat, substring, indexof
- **Date/Time**: year, month, day, hour, minute, second, now, date, time, fractionalseconds, totalseconds
- **Math**: ceiling, floor, round
- **Geographic**: geo.distance, geo.intersects, geo.length (to clean up)
- **Lambda**: any, all

#### 2.2 `parser/exceptions.py` (152 lines)

Exception hierarchy:
```python
class ODataException(Exception):
    """Base exception for OData."""

class ODataSyntaxError(ODataException):
    """Syntax error."""

class TokenizingException(ODataSyntaxError):
    """Error during tokenization."""

class ParsingException(ODataSyntaxError):
    """Error during parsing."""

class UnsupportedFunctionException(ODataException):
    """Unsupported function."""

class ArgumentTypeException(ODataException):
    """Argument type error."""
```

**Usage example:**
```python
from django_odata.core.parser import ODataLexer, ODataParser

lexer = ODataLexer()
parser = ODataParser()

query = "name eq 'John' and age gt 30"
tokens = lexer.tokenize(query)
ast = parser.parse(tokens)

# ast is a BoolOp with And and two Compare nodes
```

---

### 3. Rewrite (AST Transformers)

**Source**: Copied from `odata-query`
**Total**: 224 lines (90 + 134)
**Purpose**: Transform and manipulate AST nodes.

#### 3.1 `rewrite.py` (90 lines)

**AliasRewriter** - Replaces aliases:
```python
from django_odata.core.rewrite import AliasRewriter

# Define aliases
aliases = {
    'author_name': 'author/name',
    'post_count': 'posts/count()',
}

rewriter = AliasRewriter(aliases)
new_ast = rewriter.visit(original_ast)

# author_name eq 'John' → author/name eq 'John'
```

**IdentifierStripper** - Removes prefixes:
```python
from django_odata.core.rewrite import IdentifierStripper
from django_odata.core import ast

# Remove 'author' from the expression
stripper = IdentifierStripper(ast.Identifier('author'))
new_ast = stripper.visit(original_ast)

# author/name → name
```

#### 3.2 `typing.py` (134 lines)

**Type Inference** for AST nodes:

```python
from django_odata.core import typing

# Validate types
typing.typecheck(
    node=string_node,
    expected_type=ast.String,
    field_name='name'
)  # Raises ArgumentTypeException if not String

# Infer type
node_type = typing.infer_type(node)
# → ast.Boolean, ast.Integer, ast.String, etc.

# Infer function return type
return_type = typing.infer_return_type(call_node)
# contains() → ast.Boolean
# length() → ast.Integer
# tolower() → ast.String
```

#### 3.3 `utils.py` (35 lines)

**AST Utilities:**
```python
from django_odata.core.utils import expression_relative_to_identifier
from django_odata.core import ast

# Make expression relative to an identifier
identifier = ast.Identifier('author')
new_expr = expression_relative_to_identifier(identifier, expression)

# author/posts/any(p: p/title eq 'Hello')
# → posts/any(p: p/title eq 'Hello')
```

---

### 4. Query (OData Query Models)

**Source**: Original code
**Total**: 475 lines
**Purpose**: Models and parsing of complete OData queries.

#### 4.1 `query/models.py` (137 lines)

Models for representing OData queries:

```python
from django_odata.core.query.models import ODataQuery, ExpandItem, OrderByItem

@dataclass
class ODataQuery:
    """Represents a complete OData query."""
    filter: Optional[str] = None           # $filter=name eq 'John'
    select: Optional[List[str]] = None     # $select=name,age
    expand: Optional[List[ExpandItem]] = None  # $expand=posts($select=title)
    orderby: Optional[List[OrderByItem]] = None  # $orderby=name asc
    top: Optional[int] = None              # $top=10
    skip: Optional[int] = None             # $skip=20
    count: bool = False                    # $count=true

@dataclass
class ExpandItem:
    """$expand=posts($select=title;$top=5)"""
    field: str                             # 'posts'
    select: Optional[List[str]] = None     # ['title']
    filter: Optional[str] = None
    orderby: Optional[List[OrderByItem]] = None
    top: Optional[int] = None
    skip: Optional[int] = None
    expand: Optional[List['ExpandItem']] = None  # Nested expands

@dataclass
class OrderByItem:
    """$orderby=name asc,age desc"""
    field: str                             # 'name'
    direction: str = 'asc'                 # 'asc' | 'desc'
```

#### 4.2 `query/parser.py` (232 lines)

Parser for query strings to `ODataQuery`:

```python
from django_odata.core.query import parse_odata_query

# Parse query string
query_params = {
    'filter': "name eq 'John' and age gt 30",
    'select': 'name,age,posts',
    'expand': 'posts($select=title;$top=5),author',
    'orderby': 'name asc,age desc',
    'top': '10',
    'skip': '20',
    'count': 'true',
}

odata_query = parse_odata_query(query_params)

# Access fields
print(odata_query.filter)  # "name eq 'John' and age gt 30"
print(odata_query.select)  # ['name', 'age', 'posts']
print(odata_query.top)     # 10
```

#### 4.3 `query/validators.py` (94 lines)

Validators for OData parameters:

```python
from django_odata.core.query.validators import (
    validate_top,
    validate_skip,
    validate_orderby,
)

# Validate that top is a positive integer
validate_top('10')    # OK
validate_top('-5')    # Raises ValidationError

# Validate that skip is a non-negative integer
validate_skip('20')   # OK
validate_skip('abc')  # Raises ValidationError
```

---

### 5. Filter (Filter Engine)

**Source**: Original code
**Total**: 327 lines
**Purpose**: Generic framework-agnostic filter engine.

#### 5.1 `filter/engine.py` (151 lines)

```python
from django_odata.core.filter import get_filter_engine

# Get the filter engine
engine = get_filter_engine()

# Apply filter to a list of dicts
data = [
    {'name': 'John', 'age': 30},
    {'name': 'Jane', 'age': 25},
    {'name': 'Bob', 'age': 35},
]

filtered = engine.filter(
    data=data,
    filter_expr="age gt 25 and name ne 'Bob'"
)

# filtered = [{'name': 'John', 'age': 30}]
```

#### 5.2 `filter/operators.py` (131 lines)

Filter operators:

```python
# Comparison
eq(a, b)         # a == b
ne(a, b)         # a != b
lt(a, b)         # a < b
le(a, b)         # a <= b
gt(a, b)         # a > b
ge(a, b)         # a >= b

# String
contains(s, substr)      # substr in s
startswith(s, prefix)    # s.startswith(prefix)
endswith(s, suffix)      # s.endswith(suffix)

# Logical
and_(a, b)       # a and b
or_(a, b)        # a or b
not_(a)          # not a
```

---

### 6. DTOs (Data Transfer Objects)

**Source**: Original code
**Total**: 454 lines
**Purpose**: Conversion between Django models and DTOs.

#### 6.1 `dtos/base.py` (290 lines)

Base classes for DTOs:

```python
from django_odata.core.dtos.base import BaseDTO

class UserDTO(BaseDTO):
    id: int
    name: str
    email: str
    posts: List['PostDTO'] = []
```

#### 6.2 `dtos/converter.py` (156 lines)

Converters:

```python
from django_odata.core.dtos.converter import ModelToDTOConverter

converter = ModelToDTOConverter()

# Model → DTO
user_dto = converter.to_dto(user_model, UserDTO)

# DTO → Model
user_model = converter.from_dto(user_dto, User)
```

---

### 7. Selector (Base Selector)

**Source**: Original code
**Total**: 222 lines
**Purpose**: Protocol/Interface for selectors.

#### 7.1 `selector/base.py` (209 lines)

```python
from django_odata.core.selector.base import BaseSelector
from django_odata.core.query.models import ODataQuery

class BaseSelector(Protocol):
    """Protocol for selectors that apply OData queries."""

    def apply_query(
        self,
        queryset: Any,
        odata_query: ODataQuery
    ) -> Any:
        """Applies an OData query to the queryset."""
        ...

    def apply_filter(self, queryset: Any, filter_expr: str) -> Any:
        """Applies $filter."""
        ...

    def apply_select(self, queryset: Any, fields: List[str]) -> Any:
        """Applies $select."""
        ...

    def apply_expand(self, queryset: Any, expands: List[ExpandItem]) -> Any:
        """Applies $expand."""
        ...
```

---

### 8. Intent (Protocol-Agnostic Query)

**Source**: Original code
**Purpose**: Protocol-agnostic query representation, decoupled from OData.

#### 8.1 `intent/models.py`

Models for representing queries in an agnostic way:

```python
from fc_selector.core.intent import (
    QueryIntent,
    FilterIntent,
    SelectIntent,
    ExpandIntent,
    OrderIntent,
    PaginationIntent,
)

# QueryIntent is independent of the OData protocol
intent = QueryIntent(
    filter=FilterIntent(expression="status eq 'active'"),
    select=SelectIntent(fields=["id", "name"]),
    expand=ExpandIntent(relations={"author": QueryIntent()}),
    orderby=OrderIntent.from_tuples([("created_at", "desc")]),
    pagination=PaginationIntent(limit=10, offset=0),
)
```

#### 8.2 `intent/converters.py`

Bidirectional converters:

```python
from fc_selector.core.intent import odata_query_to_intent, intent_to_odata_query

# ODataQuery → QueryIntent
intent = odata_query_to_intent(odata_query)

# QueryIntent → ODataQuery
odata_query = intent_to_odata_query(intent)
```

---

### 9. Filters (Type-Safe Fluent API)

**Source**: Original code
**Purpose**: Type-safe fluent API for building queries without strings.

#### 9.1 `filters/fields.py` - Field Class

```python
from fc_selector.core.filters import Field

# Comparisons
Field("name").eq("John")           # name eq 'John'
Field("age").gt(18)                # age gt 18
Field("status").ne("deleted")      # status ne 'deleted'

# Null checks
Field("deleted_at").is_null()      # deleted_at eq null

# String operations
Field("name").contains("john")     # contains(name, 'john')
Field("email").startswith("admin") # startswith(email, 'admin')

# Collections
Field("status").is_in(["a", "b"])  # status in ('a', 'b')

# Range
Field("price").between(10, 100)    # price ge 10 and price le 100

# Nested fields
Field("author.name").eq("John")    # author/name eq 'John'
```

#### 9.2 `filters/expressions.py` - Expression Class

```python
# Python operators for composition
expr1 = Field("status").eq("active")
expr2 = Field("age").gt(18)

# AND: &
combined = expr1 & expr2

# OR: |
alternative = expr1 | expr2

# NOT: ~
negated = ~expr1

# Complex
complex_expr = (
    (Field("status").eq("active") & Field("age").gt(18))
    | Field("vip").eq(True)
)
```

#### 9.3 `filters/expand.py` - Expand Class

```python
from fc_selector.core.filters import Expand, OrderBy

# Simple expand
Expand("author")

# Expand with nested options
Expand("author").select("id", "name", "email")

# Expand with filter
Expand("comments").filter(Field("approved").eq(True))

# Full expand
Expand("comments")
    .select("id", "text")
    .filter(Field("approved").eq(True))
    .orderby(OrderBy("created_at").desc())
    .top(5)

# Nested expand
Expand("author").expand(
    Expand("profile").select("avatar", "bio")
)
```

#### 9.4 `filters/orderby.py` - OrderBy Class

```python
from fc_selector.core.filters import OrderBy

# Ascending (default)
OrderBy("name")
OrderBy("name").asc()

# Descending
OrderBy("created_at").desc()
```

#### 9.5 Integration with QueryBuilder

```python
from fc_selector.core.query_builder import QueryBuilder
from fc_selector.core.filters import Field, Expand, OrderBy

# Fully type-safe query
intent = (
    QueryBuilder()
    .where(Field("status").eq("published") & Field("rating").gt(4.0))
    .select("id", "title", "rating")
    .expand(
        Expand("author").select("id", "name"),
        Expand("comments")
            .filter(Field("approved").eq(True))
            .orderby(OrderBy("created_at").desc())
            .top(5)
    )
    .orderby(OrderBy("created_at").desc())
    .top(10)
    .build()  # Returns QueryIntent
)

# Execute directly (without text parsing)
results = selector.execute(intent)
```

#### 9.6 Custom Filter Parser (Dependency Injection)

The `QueryBuilder` accepts a custom filter parser for testing or alternative query languages:

```python
from fc_selector.core.query_builder import QueryBuilder
from fc_selector.core.ast import Node

def my_custom_parser(expression: str) -> Node:
    """Custom parser implementation."""
    # Your parsing logic here
    ...

# Use custom parser
builder = QueryBuilder(filter_parser=my_custom_parser)
builder.filter("my custom syntax").build()
```

---

### 10. Utils

**Source**: Copied from `odata-query`
**Total**: 35 lines
**Purpose**: Utilities for manipulating AST.

See section 3.3 above.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                   DJANGO_ODATA/CORE                         │
│                  (Framework-Agnostic)                       │
└─────────────────────────────────────────────────────────────┘

    ┌──────────────┐
    │ Query String │  "$filter=name eq 'John'&$select=name,age"
    └──────┬───────┘
           │
           ▼
    ┌──────────────┐
    │ query/       │  parse_odata_query()
    │ parser.py    │  ───────────────────────────►  ODataQuery
    └──────┬───────┘                                    │
           │                                            │
           │ $filter string                             │
           ▼                                            ▼
    ┌──────────────┐                            ┌──────────────┐
    │ parser/      │                            │ query/       │
    │ grammar.py   │  Lexer + Parser            │ models.py    │
    │              │  ───────────────►  AST     │              │
    └──────┬───────┘                    │       └──────────────┘
           │                            │
           │                            ▼
           │                     ┌──────────────┐
           │                     │ ast/         │
           │                     │ nodes.py     │  40+ node types
           │                     │              │  (immutable)
           │                     └──────┬───────┘
           │                            │
           ▼                            ▼
    ┌──────────────┐            ┌──────────────┐
    │ typing.py    │            │ visitor.py   │  NodeVisitor
    │              │◄───────────┤              │  NodeTransformer
    │ Type         │            │ Visitor      │
    │ Inference    │            │ Pattern      │
    └──────────────┘            └──────┬───────┘
                                       │
                                       ▼
                                ┌──────────────┐
                                │ rewrite.py   │  AliasRewriter
                                │              │  IdentifierStripper
                                │ AST          │
                                │ Transformers │
                                └──────┬───────┘
                                       │
                                       ▼
                            ┌──────────────────────┐
                            │ django/visitors/     │  (Django-specific)
                            │ filter_visitor.py    │
                            │                      │
                            │ AST → Django Q       │
                            └──────────────────────┘
```

---

## Data Flow

### 1. Parsing an OData Query

```python
# INPUT: Query string
query_string = "name eq 'John' and age gt 30"

# STEP 1: Lexer tokenizes
lexer = ODataLexer()
tokens = lexer.tokenize(query_string)
# → [IDENTIFIER('name'), EQ, STRING('John'), AND, IDENTIFIER('age'), GT, INTEGER(30)]

# STEP 2: Parser generates AST
parser = ODataParser()
ast = parser.parse(tokens)
# → BoolOp(
#     op=And(),
#     values=[
#         Compare(Eq(), Identifier('name'), String('John')),
#         Compare(Gt(), Identifier('age'), Integer('30', 30))
#     ]
#   )

# STEP 3: Type checking (optional)
typing.typecheck(ast.values[0].left, ast.Identifier, 'name')

# STEP 4: Rewrite (optional)
aliases = {'full_name': 'name'}
rewriter = AliasRewriter(aliases)
new_ast = rewriter.visit(ast)

# STEP 5: Visitor (framework-specific)
# See django/visitors/ to transform to Django Q
```

### 2. Parsing a Complete Query

```python
from django_odata.core.query import parse_odata_query

# INPUT: Query params
params = {
    'filter': "name eq 'John'",
    'select': 'name,age',
    'expand': 'posts($select=title)',
    'top': '10',
}

# OUTPUT: ODataQuery
odata_query = parse_odata_query(params)

# ┌─────────────────┐
# │ ODataQuery      │
# ├─────────────────┤
# │ filter: str     │ → "name eq 'John'"
# │ select: [str]   │ → ['name', 'age']
# │ expand: [...]   │ → [ExpandItem(field='posts', select=['title'])]
# │ top: int        │ → 10
# └─────────────────┘
```

---

## Usage Examples

### Example 1: Parse and Traverse AST

```python
from django_odata.core.parser import ODataLexer, ODataParser
from django_odata.core.ast import visitor

# Parse query
lexer = ODataLexer()
parser = ODataParser()
query = "contains(name, 'John') and age gt 30"
tokens = lexer.tokenize(query)
ast = parser.parse(tokens)

# Traverse AST
class MyVisitor(visitor.NodeVisitor):
    def visit_Call(self, node):
        print(f"Function: {node.func.name}")
        print(f"Args: {[arg for arg in node.args]}")

    def visit_Compare(self, node):
        print(f"Comparison: {node.left} {node.comparator} {node.right}")

v = MyVisitor()
v.visit(ast)

# Output:
# Function: contains
# Args: [Identifier('name'), String('John')]
# Comparison: Identifier('age') Gt() Integer('30', 30)
```

### Example 2: Transform AST

```python
from django_odata.core.ast import visitor, nodes

class UppercaseStrings(visitor.NodeTransformer):
    """Converts all strings to uppercase."""

    def visit_String(self, node):
        return nodes.String(
            val=f"'{node.py_val.upper()}'",
            py_val=node.py_val.upper()
        )

transformer = UppercaseStrings()
new_ast = transformer.visit(ast)

# "name eq 'john'" → "name eq 'JOHN'"
```

### Example 3: Parse Complete Query

```python
from django_odata.core.query import parse_odata_query

query_params = {
    'filter': "status eq 'active' and created gt 2024-01-01",
    'select': 'id,name,status',
    'expand': 'posts($select=title,body;$top=5),author($select=name)',
    'orderby': 'created desc',
    'top': '20',
    'skip': '0',
    'count': 'true',
}

odata_query = parse_odata_query(query_params)

print(f"Filter: {odata_query.filter}")
print(f"Select: {odata_query.select}")
print(f"Expand: {odata_query.expand}")
print(f"Top: {odata_query.top}")
print(f"Count: {odata_query.count}")
```

---

## Important Notes

### 1. Framework-Agnostic

**All code in `core/` does NOT depend on Django.** This allows:
- Reuse in other frameworks (Flask, FastAPI)
- Testing without Django
- Standalone use for OData validation

### 2. Security Features

The library includes built-in security measures:
- **Field validation**: `InvalidFieldError` blocks access to private fields (`_password`)
- **Input length limits**: `MAX_FILTER_LENGTH=4000` prevents DoS attacks
- **Type-safe API**: The `Field`, `Expand`, `OrderBy` classes prevent injection

### 3. Performance Optimizations

- **Thread-local parser caching**: Lexer/parser instances are cached per-thread
- **Dependency injection**: `QueryBuilder` accepts custom filter parsers

### 4. Immutability

**All AST nodes are immutable** (`frozen=True`). To modify them, you need to create new nodes with `NodeTransformer`.

### 5. Large Parser (721 lines)

The `grammar.py` parser is large because it supports **all** OData functions:
- String functions (20+)
- Date/time functions (15+)
- Math functions (10+)
- Geographic functions (5+)
- Lambda expressions (any/all)

**Cleanup plan**: See `/PARSER_CLEANUP_TASKS.md` to remove unused functions.

### 6. Credits

Much of the core (AST, Parser, Rewrite, Typing, Utils) is **copied from [odata-query](https://github.com/gorilla-co/odata-query)**:
- License: MIT
- Authors: gorilla-co
- Modifications: Imports updated to use `django_odata.core.*`

All copied files have headers with original credits.

---

## Next Steps

1. **Tests** (`/tests/core/`):
   - Test for each AST node
   - Test for parser (functions, lambdas)
   - Test for visitors
   - Test for rewriters

2. **Optimization**:
   - Remove unused OData functions
   - Reduce parser from 721 to ~500 lines
   - Coverage >90%

3. **Documentation**:
   - Create `SUPPORTED_ODATA_FUNCTIONS.md`
   - Usage examples for each function
   - Tutorials

---

## Summary

| Module | Lines | Source | Purpose |
|--------|-------|--------|---------|
| **ast/** | 1,150 | odata-query | Immutable AST nodes + Visitor pattern |
| **parser/** | 921 | odata-query | OData Lexer/Parser → AST (SLY) |
| **rewrite.py** | 90 | odata-query | AST transformers (aliases, stripping) |
| **typing.py** | 134 | odata-query | Type inference for nodes |
| **utils.py** | 35 | odata-query | AST utils |
| **query/** | 475 | Original | OData query models and parsing |
| **filter/** | 327 | Original | Generic filter engine |
| **dtos/** | 454 | Original | Model ↔ DTO conversion |
| **selector/** | 222 | Original | Base protocol for selectors |
| **intent/** | ~300 | Original | Protocol-agnostic QueryIntent |
| **filters/** | ~500 | Original | Type-safe fluent API (Field, Expand, OrderBy) |
| **TOTAL** | **~4,600** | 50% / 50% | Framework-agnostic core |

**Architecture**: Clean, extensible, testable, reusable

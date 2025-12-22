# django_odata/core - Framework-Agnostic OData Layer

**Total**: 3,823 línies de codi Python distribuïdes en 7 submòduls.

Aquest package conté tota la lògica central d'OData que **no depèn de Django ni cap altre framework**. Pot ser reutilitzat en altres contexts (Flask, FastAPI, standalone, etc.).

---

## 📋 Índex

1. [Estructura General](#estructura-general)
2. [Submòduls](#submòduls)
   - [AST (Abstract Syntax Tree)](#1-ast-abstract-syntax-tree)
   - [Parser](#2-parser-lexerparser-odata)
   - [Rewrite](#3-rewrite-ast-transformers)
   - [Query](#4-query-odata-query-models)
   - [Filter](#5-filter-filter-engine)
   - [DTOs](#6-dtos-data-transfer-objects)
   - [Selector](#7-selector-base-selector)
   - [Utils](#8-utils)
3. [Diagrama d'Arquitectura](#diagrama-darquitectura)
4. [Flux de Dades](#flux-de-dades)
5. [Exemples d'Ús](#exemples-dús)

---

## Estructura General

```
django_odata/core/
├── __init__.py                    # Entry point: parse_odata_query, get_filter_engine
│
├── ast/                           # ✅ Copiat de odata-query (1,150 línies)
│   ├── nodes.py (729 línies)     # 40+ tipus de nodes AST
│   ├── visitor.py (266 línies)   # NodeVisitor, NodeTransformer
│   └── __init__.py (155 línies)  # Exports
│
├── parser/                        # ✅ Copiat de odata-query (921 línies)
│   ├── grammar.py (721 línies)   # ODataLexer, ODataParser (SLY)
│   ├── exceptions.py (152 línies) # OData exceptions
│   └── __init__.py (48 línies)   # Exports
│
├── rewrite.py (90 línies)        # ✅ Copiat de odata-query - AST transformers
├── typing.py (134 línies)        # ✅ Copiat de odata-query - Type inference
├── utils.py (35 línies)          # ✅ Copiat de odata-query - AST utils
│
├── query/                         # 📦 Original (475 línies)
│   ├── models.py (137 línies)    # ODataQuery, ExpandItem, OrderByItem
│   ├── parser.py (232 línies)    # parse_odata_query()
│   ├── validators.py (94 línies) # Query validators
│   └── __init__.py (14 línies)   # Exports
│
├── filter/                        # 📦 Original (327 línies)
│   ├── engine.py (151 línies)    # FilterEngine genèric
│   ├── operators.py (131 línies) # Filter operators
│   ├── exceptions.py (28 línies) # Filter exceptions
│   └── __init__.py (17 línies)   # Exports
│
├── dtos/                          # 📦 Original (454 línies)
│   ├── base.py (290 línies)      # Base DTO classes
│   ├── converter.py (156 línies) # Model ↔ DTO converters
│   └── __init__.py (8 línies)    # Exports
│
└── selector/                      # 📦 Original (222 línies)
    ├── base.py (209 línies)      # BaseSelector protocol
    └── __init__.py (13 línies)   # Exports
```

**Llegenda:**
- ✅ = Copiat de [odata-query](https://github.com/gorilla-co/odata-query) (MIT License)
- 📦 = Codi original nostre

---

## Submòduls

### 1. AST (Abstract Syntax Tree)

**Origen**: Copiat de `odata-query`
**Total**: 1,150 línies
**Propòsit**: Representar expressions OData com arbres de nodes immutables.

#### 1.1 `ast/nodes.py` (729 línies) - El fitxer més gran

Defineix 40+ tipus de nodes AST amb `@dataclass(frozen=True)`:

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

# També: Float, Boolean, Date, DateTime, Duration, Null
```

**Comparadors:**
```python
@dataclass(frozen=True)
class Eq(_Comparator):
    """Equality (eq)"""

# També: NotEq, Lt, LtE, Gt, GtE
```

**Expressions:**
```python
@dataclass(frozen=True)
class Compare(_Node):
    """name eq 'John'"""
    comparator: _Comparator  # Eq, NotEq, etc.
    left: _Node              # Identifier('name')
    right: _Node             # String('John')

@dataclass(frozen=True)
class BoolOp(_Node):
    """name eq 'John' and age gt 30"""
    op: _BoolOperator        # And, Or
    values: List[_Node]      # [Compare(...), Compare(...)]

@dataclass(frozen=True)
class Call(_Node):
    """contains(name, 'John')"""
    func: Identifier         # Identifier('contains')
    args: List[_Node]        # [Identifier('name'), String('John')]
```

**Lambda Expressions:**
```python
@dataclass(frozen=True)
class CollectionLambda(_Node):
    """comments/any(c: c/rating gt 4)"""
    collection: _Node        # Attribute('comments')
    expression: _Node        # Compare(...)
    iterator_variable_name: str  # 'c'
```

**Identificadors:**
```python
@dataclass(frozen=True)
class Identifier(_Node):
    """name"""
    name: str
    namespace: Tuple[str, ...] = ()

@dataclass(frozen=True)
class Attribute(_Node):
    """author/name"""
    owner: _Node  # Identifier('author')
    attr: str     # 'name'
```

#### 1.2 `ast/visitor.py` (266 línies)

Implementació del **Visitor Pattern** (PEP 544):

```python
class NodeVisitor:
    """Base class per traversar AST."""

    def visit(self, node: nodes._Node) -> Any:
        """Crida al mètode visit_<NodeType> apropiat."""
        method = "visit_" + node.__class__.__name__
        visitor = getattr(self, method, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node: nodes._Node) -> Any:
        """Fallback per nodes sense visitor."""
        return node

class NodeTransformer(NodeVisitor):
    """Visitor que permet modificar nodes."""

    def generic_visit(self, node: nodes._Node) -> nodes._Node:
        """Visita recursivament i retorna node transformat."""
        # Traversa i transforma fills
        # Retorna nou node amb fills transformats
```

**Exemple d'ús:**
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

**Origen**: Copiat de `odata-query`
**Total**: 921 línies
**Propòsit**: Parsejar expressions OData a AST utilitzant SLY (Sly Lex-Yacc).

#### 2.1 `parser/grammar.py` (721 línies) - El segon fitxer més gran

**ODataLexer** - Tokenització:
```python
class ODataLexer(Lexer):
    tokens = {
        # Identificadors i literals
        IDENTIFIER, STRING, INTEGER, FLOAT,

        # Comparadors
        EQ, NE, LT, LE, GT, GE,

        # Operadors lògics
        AND, OR, NOT,

        # Funcions
        CONTAINS, STARTSWITH, ENDSWITH, TOLOWER, TOUPPER,
        YEAR, MONTH, DAY, HOUR, MINUTE, SECOND,

        # Lambda
        ANY, ALL,

        # Geographic (per netejar més endavant)
        GEO_DISTANCE, GEO_INTERSECTS,

        # Altres
        LPAREN, RPAREN, COMMA, SLASH,
    }

    # Regles de tokenització
    @_(r'[a-zA-Z_][a-zA-Z0-9_]*')
    def IDENTIFIER(self, t):
        # Converteix keywords (eq, and, contains, etc.)
        t.type = self.keywords.get(t.value, 'IDENTIFIER')
        return t

    @_(r"'([^'\\\\]|\\\\.)*'")
    def STRING(self, t):
        t.value = t.value[1:-1]  # Remove quotes
        return t
```

**ODataParser** - Parsing a AST:
```python
class ODataParser(Parser):
    tokens = ODataLexer.tokens

    # Gramàtica
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

**Funcions suportades:**
- **String**: contains, startswith, endswith, tolower, toupper, trim, length, concat, substring, indexof
- **Date/Time**: year, month, day, hour, minute, second, now, date, time, fractionalseconds, totalseconds
- **Math**: ceiling, floor, round
- **Geographic**: geo.distance, geo.intersects, geo.length (per netejar)
- **Lambda**: any, all

#### 2.2 `parser/exceptions.py` (152 línies)

Jerarquia d'excepcions:
```python
class ODataException(Exception):
    """Base exception per OData."""

class ODataSyntaxError(ODataException):
    """Error de sintaxi."""

class TokenizingException(ODataSyntaxError):
    """Error durant tokenització."""

class ParsingException(ODataSyntaxError):
    """Error durant parsing."""

class UnsupportedFunctionException(ODataException):
    """Funció no suportada."""

class ArgumentTypeException(ODataException):
    """Error de tipus d'argument."""
```

**Exemple d'ús:**
```python
from django_odata.core.parser import ODataLexer, ODataParser

lexer = ODataLexer()
parser = ODataParser()

query = "name eq 'John' and age gt 30"
tokens = lexer.tokenize(query)
ast = parser.parse(tokens)

# ast és un BoolOp amb And i dos Compare nodes
```

---

### 3. Rewrite (AST Transformers)

**Origen**: Copiat de `odata-query`
**Total**: 224 línies (90 + 134)
**Propòsit**: Transformar i manipular AST nodes.

#### 3.1 `rewrite.py` (90 línies)

**AliasRewriter** - Reemplaça àlies:
```python
from django_odata.core.rewrite import AliasRewriter

# Defineix àlies
aliases = {
    'author_name': 'author/name',
    'post_count': 'posts/count()',
}

rewriter = AliasRewriter(aliases)
new_ast = rewriter.visit(original_ast)

# author_name eq 'John' → author/name eq 'John'
```

**IdentifierStripper** - Elimina prefixos:
```python
from django_odata.core.rewrite import IdentifierStripper
from django_odata.core import ast

# Elimina 'author' de l'expressió
stripper = IdentifierStripper(ast.Identifier('author'))
new_ast = stripper.visit(original_ast)

# author/name → name
```

#### 3.2 `typing.py` (134 línies)

**Type Inference** per AST nodes:

```python
from django_odata.core import typing

# Valida tipus
typing.typecheck(
    node=string_node,
    expected_type=ast.String,
    field_name='name'
)  # Raises ArgumentTypeException si no és String

# Infereix tipus
node_type = typing.infer_type(node)
# → ast.Boolean, ast.Integer, ast.String, etc.

# Infereix tipus de retorn de funcions
return_type = typing.infer_return_type(call_node)
# contains() → ast.Boolean
# length() → ast.Integer
# tolower() → ast.String
```

#### 3.3 `utils.py` (35 línies)

**Utilities per AST:**
```python
from django_odata.core.utils import expression_relative_to_identifier
from django_odata.core import ast

# Fa l'expressió relativa a un identificador
identifier = ast.Identifier('author')
new_expr = expression_relative_to_identifier(identifier, expression)

# author/posts/any(p: p/title eq 'Hello')
# → posts/any(p: p/title eq 'Hello')
```

---

### 4. Query (OData Query Models)

**Origen**: Codi original
**Total**: 475 línies
**Propòsit**: Models i parsing de queries OData completes.

#### 4.1 `query/models.py` (137 línies)

Models per representar queries OData:

```python
from django_odata.core.query.models import ODataQuery, ExpandItem, OrderByItem

@dataclass
class ODataQuery:
    """Representa una query OData completa."""
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

#### 4.2 `query/parser.py` (232 línies)

Parser de query strings a `ODataQuery`:

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

# Accedeix als camps
print(odata_query.filter)  # "name eq 'John' and age gt 30"
print(odata_query.select)  # ['name', 'age', 'posts']
print(odata_query.top)     # 10
```

#### 4.3 `query/validators.py` (94 línies)

Validadors per paràmetres OData:

```python
from django_odata.core.query.validators import (
    validate_top,
    validate_skip,
    validate_orderby,
)

# Valida que top és un enter positiu
validate_top('10')    # OK
validate_top('-5')    # Raises ValidationError

# Valida que skip és un enter no negatiu
validate_skip('20')   # OK
validate_skip('abc')  # Raises ValidationError
```

---

### 5. Filter (Filter Engine)

**Origen**: Codi original
**Total**: 327 línies
**Propòsit**: Motor genèric de filtres framework-agnostic.

#### 5.1 `filter/engine.py` (151 línies)

```python
from django_odata.core.filter import get_filter_engine

# Obté el motor de filtres
engine = get_filter_engine()

# Aplica filtre a una llista de dicts
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

#### 5.2 `filter/operators.py` (131 línies)

Operadors de filtre:

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

**Origen**: Codi original
**Total**: 454 línies
**Propòsit**: Conversió entre models Django i DTOs.

#### 6.1 `dtos/base.py` (290 línies)

Classes base per DTOs:

```python
from django_odata.core.dtos.base import BaseDTO

class UserDTO(BaseDTO):
    id: int
    name: str
    email: str
    posts: List['PostDTO'] = []
```

#### 6.2 `dtos/converter.py` (156 línies)

Conversors:

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

**Origen**: Codi original
**Total**: 222 línies
**Propòsit**: Protocol/Interface per selectors.

#### 7.1 `selector/base.py` (209 línies)

```python
from django_odata.core.selector.base import BaseSelector
from django_odata.core.query.models import ODataQuery

class BaseSelector(Protocol):
    """Protocol per selectors que apliquen queries OData."""

    def apply_query(
        self,
        queryset: Any,
        odata_query: ODataQuery
    ) -> Any:
        """Aplica una query OData al queryset."""
        ...

    def apply_filter(self, queryset: Any, filter_expr: str) -> Any:
        """Aplica $filter."""
        ...

    def apply_select(self, queryset: Any, fields: List[str]) -> Any:
        """Aplica $select."""
        ...

    def apply_expand(self, queryset: Any, expands: List[ExpandItem]) -> Any:
        """Aplica $expand."""
        ...
```

---

### 8. Utils

**Origen**: Copiat de `odata-query`
**Total**: 35 línies
**Propòsit**: Utilities per manipular AST.

Veure apartat 3.3 més amunt.

---

## Diagrama d'Arquitectura

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

## Flux de Dades

### 1. Parsing d'una Query OData

```python
# INPUT: Query string
query_string = "name eq 'John' and age gt 30"

# STEP 1: Lexer tokenitza
lexer = ODataLexer()
tokens = lexer.tokenize(query_string)
# → [IDENTIFIER('name'), EQ, STRING('John'), AND, IDENTIFIER('age'), GT, INTEGER(30)]

# STEP 2: Parser genera AST
parser = ODataParser()
ast = parser.parse(tokens)
# → BoolOp(
#     op=And(),
#     values=[
#         Compare(Eq(), Identifier('name'), String('John')),
#         Compare(Gt(), Identifier('age'), Integer('30', 30))
#     ]
#   )

# STEP 3: Type checking (opcional)
typing.typecheck(ast.values[0].left, ast.Identifier, 'name')

# STEP 4: Rewrite (opcional)
aliases = {'full_name': 'name'}
rewriter = AliasRewriter(aliases)
new_ast = rewriter.visit(ast)

# STEP 5: Visitor (específic de framework)
# Veure django/visitors/ per transformar a Django Q
```

### 2. Parsing d'una Query Completa

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

## Exemples d'Ús

### Exemple 1: Parsejar i Traversar AST

```python
from django_odata.core.parser import ODataLexer, ODataParser
from django_odata.core.ast import visitor

# Parse query
lexer = ODataLexer()
parser = ODataParser()
query = "contains(name, 'John') and age gt 30"
tokens = lexer.tokenize(query)
ast = parser.parse(tokens)

# Traversa AST
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

### Exemple 2: Transform AST

```python
from django_odata.core.ast import visitor, nodes

class UppercaseStrings(visitor.NodeTransformer):
    """Converteix tots els strings a uppercase."""

    def visit_String(self, node):
        return nodes.String(
            val=f"'{node.py_val.upper()}'",
            py_val=node.py_val.upper()
        )

transformer = UppercaseStrings()
new_ast = transformer.visit(ast)

# "name eq 'john'" → "name eq 'JOHN'"
```

### Exemple 3: Parse Query Completa

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

## Notes Importants

### 1. Framework-Agnostic

**Tot el codi en `core/` NO depèn de Django.** Això permet:
- Reutilitzar en altres frameworks (Flask, FastAPI)
- Testejar sense Django
- Usar standalone per validació OData

### 2. Immutabilitat

**Tots els nodes AST són immutables** (`frozen=True`). Per modificar-los cal crear nous nodes amb `NodeTransformer`.

### 3. Parser Gran (721 línies)

El parser `grammar.py` és gran perquè suporta **totes** les funcions OData:
- String functions (20+)
- Date/time functions (15+)
- Math functions (10+)
- Geographic functions (5+)
- Lambda expressions (any/all)

**Pla de neteja**: Veure `/PARSER_CLEANUP_TASKS.md` per eliminar funcions no utilitzades.

### 4. Crèdits

Gran part del core (AST, Parser, Rewrite, Typing, Utils) està **copiat de [odata-query](https://github.com/gorilla-co/odata-query)**:
- Llicència: MIT
- Autors: gorilla-co
- Modificacions: Imports actualitzats per usar `django_odata.core.*`

Tots els fitxers copiats tenen headers amb crèdits originals.

---

## Pròxims Passos

1. **Tests** (`/tests/core/`):
   - Test per cada node AST
   - Test per parser (funcions, lambdas)
   - Test per visitors
   - Test per rewriters

2. **Optimització**:
   - Eliminar funcions OData no utilitzades
   - Reduir parser de 721 a ~500 línies
   - Coverage >90%

3. **Documentació**:
   - Crear `SUPPORTED_ODATA_FUNCTIONS.md`
   - Exemples d'ús per cada funció
   - Tutorials

---

## Resum

| Mòdul | Línies | Origen | Propòsit |
|-------|--------|--------|----------|
| **ast/** | 1,150 | odata-query | Nodes AST immutables + Visitor pattern |
| **parser/** | 921 | odata-query | Lexer/Parser OData → AST (SLY) |
| **rewrite.py** | 90 | odata-query | Transformadors AST (aliases, stripping) |
| **typing.py** | 134 | odata-query | Type inference per nodes |
| **utils.py** | 35 | odata-query | Utils AST |
| **query/** | 475 | Original | Models i parsing queries OData |
| **filter/** | 327 | Original | Motor de filtres genèric |
| **dtos/** | 454 | Original | Conversió Model ↔ DTO |
| **selector/** | 222 | Original | Protocol base per selectors |
| **TOTAL** | **3,823** | 60% / 40% | Core framework-agnostic |

**Arquitectura**: Clean, extensible, testable, reusable ✨

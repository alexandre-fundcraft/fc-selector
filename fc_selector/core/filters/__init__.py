"""
Fluent Type-Safe API for building query options.

This module provides a type-safe, IDE-friendly alternative to string-based
OData expressions. Instead of writing strings, you can use classes to build
queries programmatically.

Filter Examples:
    >>> from fc_selector.core.filters import Field
    >>>
    >>> # Simple equality
    >>> Field("name").eq("John")
    >>>
    >>> # Comparisons
    >>> Field("age").gt(18)
    >>> Field("price").between(10, 100)
    >>>
    >>> # String operations
    >>> Field("email").endswith("@example.com")
    >>>
    >>> # Logical composition
    >>> (Field("name").eq("John") & Field("age").gt(18)) | Field("status").eq("active")
    >>>
    >>> # Negation
    >>> ~Field("deleted").eq(True)
    >>>
    >>> # Nested fields
    >>> Field("author.name").eq("John")
    >>> Field("author").name.eq("John")  # Alternative syntax
    >>>
    >>> # In operator
    >>> Field("status").is_in(["active", "pending"])

Expand Examples:
    >>> from fc_selector.core.filters import Expand, Field
    >>>
    >>> # Simple expand
    >>> Expand("author")
    >>>
    >>> # Expand with select
    >>> Expand("author").select("id", "name")
    >>>
    >>> # Expand with filter
    >>> Expand("comments").filter(Field("approved").eq(True))
    >>>
    >>> # Expand with multiple options
    >>> Expand("comments").select("id", "text").filter(Field("approved").eq(True)).top(5)
    >>>
    >>> # Nested expand
    >>> Expand("author").expand(Expand("profile").select("avatar"))

OrderBy Examples:
    >>> from fc_selector.core.filters import OrderBy
    >>>
    >>> # Ascending (default)
    >>> OrderBy("name")
    >>> OrderBy("name").asc()
    >>>
    >>> # Descending
    >>> OrderBy("created_at").desc()

Full Integration with QueryBuilder:
    >>> from fc_selector.core.query_builder import QueryBuilder
    >>> from fc_selector.core.filters import Field, Expand, OrderBy
    >>>
    >>> intent = (
    ...     QueryBuilder()
    ...     .where(Field("status").eq("active") & Field("age").gt(18))
    ...     .select("id", "title")
    ...     .expand(
    ...         Expand("author").select("id", "name"),
    ...         Expand("comments").filter(Field("approved").eq(True)).top(5)
    ...     )
    ...     .orderby(OrderBy("created_at").desc(), OrderBy("title").asc())
    ...     .top(10)
    ...     .build()
    ... )
    >>>
    >>> results = selector.execute(intent)
"""

from .expand import Expand
from .expressions import Expression
from .fields import Field
from .orderby import OrderBy

__all__ = [
    "Expand",
    "Expression",
    "Field",
    "OrderBy",
]

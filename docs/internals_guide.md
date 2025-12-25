# Developer Internals Guide

This guide is intended for engineers who want to contribute to the `fc-selector` library core or understand how it works "under the hood".

## 1. Query Lifecycle

When a user makes a request like `GET /api/posts?$filter=status eq 'published'`, the following happens:

1.  **View/Selector (`odata_selector.py`):**
    *   Receives the query string.
    *   Calls `parse_odata_query` (protocol layer) to get an intermediate `ODataQuery` structure.
    *   Converts `ODataQuery` -> `QueryIntent` (Core). This step normalizes names and structure.
    *   If there are string filters, they are parsed to AST (`parse_filter`) and injected into `QueryIntent`.

2.  **Executor (`django/executor.py`):**
    *   Receives the `QueryIntent`.
    *   **Filters:** Passes the AST to `AstToDjangoQVisitor`. This traverses the tree and builds a complex `Q()` object.
    *   **Optimization (Expand/Select):** Analyzes relationships.
        *   If it's a direct relation (FK), adds `select_related`.
        *   If it's a reverse or M2M relation, creates a `Prefetch` object.
        *   **Recursion:** For `Prefetch`, the Executor calls itself (creates a new `DjangoExecutor`) to apply filters/ordering to the subquery.

## 2. Working with the AST

The AST (`fc_selector/core/ast/nodes.py`) is the abstract representation of filters.

### Adding a new OData function
If you want to support a new function, for example `years_between(date1, date2)`:

1.  **Define the AST node:** Make sure `Call` can represent it (usually yes).
2.  **Update the Parser (`protocols/odata/parsers/grammar.py`):** If special syntax is needed. If it's a standard function, the generic parser will already detect it as `Call`.
3.  **Implement in the Visitor (`django/visitors/filter_visitor.py`):**
    *   Add a method `djangofunc_years_between(self, arg1, arg2)`.
    *   This method must return a Django `Expression` (e.g., `Func` or `ExpressionWrapper`).

```python
def djangofunc_years_between(self, start, end):
    # Simplified example
    return ExtractYear(self.visit(end)) - ExtractYear(self.visit(start))
```

## 3. Debugging

If a query fails or returns incorrect data:

1.  **Verify the `QueryIntent`:** Set a breakpoint at `DjangoExecutor.execute`. Inspect the `intent` object. Is it well-formed? Does it have the correct AST?
2.  **Verify the Visitor:** If the filter fails, look at `AstToDjangoQVisitor.visit`. How is the node being translated?
3.  **Exceptions:**
    *   If you get a generic 500, the Visitor likely failed with an uncontrolled exception.
    *   Make sure the Visitor throws `core.exceptions.SelectorError` (or subclasses) so the adapter can convert it to a 400 Bad Request.

## 4. Key Directory Structure

*   `fc_selector/core`: **DO NOT TOUCH** (unless you're changing the global architecture). This is where the contracts live.
*   `fc_selector/protocols`: This is where string parsing logic lives.
*   `fc_selector/django`: This is where the ORM magic lives.
    *   `executor.py`: The unified entry point.
    *   `visitors/`: AST to Django Q translation.

## 5. Tests

Whenever you touch Core or Executor, run the full integration suite:

```bash
pytest tests/e2e/
```

These tests verify that the complete chain (Parser -> Intent -> Executor -> DB) works correctly.

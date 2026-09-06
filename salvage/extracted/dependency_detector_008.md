# `dependency_detector_008`

## Module docstring

```
Circular dependency detector for SPECKIT-008: Auto-Generate OData Serializers.

This module provides utilities to detect and resolve circular dependencies
in model relationships using graph-based cycle detection (DFS algorithm).
```

## API surface

- `ModelGraph()`
  > ModelGraph
- `CircularDependency()`
  > CircularDependency
- `build_relationship_graph(models, relationships_map)`
  > Build a directed graph of model relationships. Args: models: List of Django model classes relationships_map: Dict mapping model paths to their relationships Returns: ModelGraph object representing the relationship graph
- `detect_cycles(graph)`
  > Detect cycles in the relationship graph using DFS. Args: graph: ModelGraph object Returns: List of CircularDependency objects
  - `dfs(node, path)`
    > Depth-first search to detect cycles.
- `resolve_circular_dependencies(cycles)`
  > Resolve circular dependencies by identifying edges to skip. Strategy: Skip reverse relationships to break cycles, prioritizing forward relationships (FK, M2M, O2O). Args: cycles: List of CircularDependency objects Returns: Set of edges (from_model, to_model) to exclude from expandable_fields
- `should_include_relationship(from_model, to_model, excluded_edges)`
  > Determine if a relationship should be included in expandable_fields. Args: from_model: Source model path to_model: Target model path excluded_edges: Set of edges to exclude Returns: True if relationship should be included, False otherwise

## String constants

Templates and messages, in definition order.

### in `ModelGraph`

```
Directed graph of model relationships.
```

### in `CircularDependency`

```
Information about a circular dependency.
```


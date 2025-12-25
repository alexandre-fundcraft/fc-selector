# Code Review Action Plan

This document outlines the action plan to resolve issues identified in the comprehensive code review.

## Priority Levels

- **P0 (Critical)**: Fix immediately - blocking issues
- **P1 (High)**: Fix soon - significant impact
- **P2 (Medium)**: Technical debt - should be addressed
- **P3 (Low)**: Enhancements - nice to have

---

## P0 - Critical Issues

### 1. Fix Failing Tests (42 tests)

**Problem**: Tests are failing due to import mismatches after refactoring.

**Files to fix**:
- `tests/test_dto_base.py:54` - Import `_Unset` renamed to `Unset`
- Other test files may have similar issues

**Action**:
```python
# Before
from fc_selector.core.dtos.base import _Unset

# After
from fc_selector.core.dtos.base import Unset
```

**Verification**: Run `make test` and ensure all tests pass.

---

### 2. Remove Debug SQL Logging in Production Code

**Problem**: SQL queries logged at WARNING level pollutes production logs.

**File**: `fc_selector/django/executor.py:156`

**Current code**:
```python
logger.warning(f"[OData] SQL: {queryset.query}")
```

**Action**: Change to DEBUG level:
```python
logger.debug(f"[OData] SQL: {queryset.query}")
```

---

## P1 - High Priority Issues

### 3. Improve Exception Handling Granularity

**Problem**: Overly broad exception catching masks bugs.

**File**: `fc_selector/django/query/applier.py:113-122`

**Current code**:
```python
except (ValueError, TypeError, AttributeError, KeyError) as e:
    logger.error(f"Error processing OData query parameters: {e}")
    raise ODataFilterError(...)
```

**Action**: Handle exceptions more specifically:
```python
except ValueError as e:
    logger.error(f"Invalid value in OData query: {e}")
    raise ODataFilterError(f"Invalid value: {e}")
except TypeError as e:
    logger.error(f"Type error in OData query: {e}")
    raise ODataFilterError(f"Type error: {e}")
# etc.
```

---

### 4. Add Cache Size Limits

**Problem**: DTO caches grow indefinitely without limits.

**File**: `fc_selector/core/dtos/base.py:43-45`

**Current code**:
```python
_TYPE_HINTS_CACHE: dict[type, dict[str, Any]] = {}
_RELATIONSHIP_INFO_CACHE: dict[type, dict[str, dict[str, Any]]] = {}
_DTO_FIELDS_CACHE: dict[type, set[str]] = {}
```

**Action**: Use `functools.lru_cache` with maxsize:
```python
from functools import lru_cache

@lru_cache(maxsize=256)
def _get_type_hints_cached(cls: type) -> dict[str, Any]:
    return get_type_hints(cls)
```

---

### 5. Fix Nested Executor Configuration Loss

**Problem**: Nested executors don't inherit field_aliases and allowed_fields.

**File**: `fc_selector/django/executor.py:302-303`

**Current code**:
```python
nested_executor = DjangoExecutor()
```

**Action**: Pass configuration to nested executor:
```python
nested_executor = DjangoExecutor(
    field_aliases=self._field_aliases,
    allowed_fields=self._allowed_fields,
    expandable_fields=self._expandable_fields,
)
```

---

## P2 - Medium Priority (Technical Debt)

### 6. Remove Dead Code

**Problem**: Unused `_extract_dto_class` method.

**File**: `fc_selector/django/drf/serializers/dto_serializer.py:222`

**Action**: Verify method is unused and remove it.

---

### 7. Lazy Singleton Initialization

**Problem**: Module-level singleton instantiation at import time.

**File**: `fc_selector/django/query/applier.py:125-126`

**Current code**:
```python
_applier = QueryApplier()
```

**Action**: Use lazy initialization:
```python
_applier: QueryApplier | None = None

def get_applier() -> QueryApplier:
    global _applier
    if _applier is None:
        _applier = QueryApplier()
    return _applier
```

---

### 8. Profile and Optimize Expand Performance

**Problem**: Relationship expansion is 700x slower than baseline.

**Files**: `fc_selector/django/executor.py`

**Action**:
1. Profile with `cProfile` to identify bottlenecks
2. Consider batch loading patterns
3. Review recursive DTO conversion
4. Add performance tests with thresholds

---

## P3 - Low Priority (Enhancements)

### 9. Replace DTO Naming Convention Detection

**Problem**: Relying on "DTO" suffix for type detection is fragile.

**File**: `fc_selector/core/dtos/base.py:117`

**Current code**:
```python
return bool(field_type.__name__.endswith("DTO"))
```

**Action**: Use base class check:
```python
return isinstance(field_type, type) and issubclass(field_type, BaseODataDTO)
```

---

### 10. Move Dynamic Imports to Module Level

**Problem**: Dynamic imports in hot paths hurt performance.

**File**: `fc_selector/core/dtos/base.py:263`

**Action**: Move import to module level with lazy loading pattern.

---

## Implementation Order

1. **Phase 1 - Critical** (Today)
   - [ ] Fix failing tests (Issue #1)
   - [ ] Fix debug logging (Issue #2)

2. **Phase 2 - High Priority** (This Week)
   - [ ] Improve exception handling (Issue #3)
   - [ ] Add cache limits (Issue #4)
   - [ ] Fix nested executor config (Issue #5)

3. **Phase 3 - Technical Debt** (Next Sprint)
   - [ ] Remove dead code (Issue #6)
   - [ ] Lazy singleton (Issue #7)
   - [ ] Profile expand performance (Issue #8)

4. **Phase 4 - Enhancements** (Backlog)
   - [ ] Replace DTO naming convention (Issue #9)
   - [ ] Optimize imports (Issue #10)

---

## Verification Checklist

After implementing fixes:

- [ ] All tests pass (`make test`)
- [ ] Linting passes (`make lint`)
- [ ] Type checking passes (`make typecheck`)
- [ ] Performance benchmarks don't regress
- [ ] Documentation is updated if needed

---

## Notes

- Always run the full test suite after each change
- Create separate commits for each issue
- Update CHANGELOG.md with fixes

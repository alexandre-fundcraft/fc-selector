# Installation

## Requirements

- Python 3.11+
- Django 4.2+
- Django REST Framework 3.12+

## Install

```bash
pip install fc-selector
```

Or with uv:

```bash
uv add fc-selector
```

## Configuration

Add `fc_selector` to your `INSTALLED_APPS`:

```python
# settings.py
INSTALLED_APPS = [
    # ...
    'rest_framework',
    'fc_selector',
]
```

That's it! No additional configuration required.

## Optional: DRF Spectacular

For automatic OpenAPI/Swagger documentation of OData parameters, install drf-spectacular:

```bash
pip install drf-spectacular
```

```python
# settings.py
INSTALLED_APPS = [
    # ...
    'drf_spectacular',
]

REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}
```

## Development Installation

For contributing or development:

```bash
git clone https://github.com/alexandre-fundcraft/fc-selector.git
cd fc-selector

# Using uv (recommended)
uv sync --group dev

# Using pip
pip install -e ".[dev]"
```

## Verify Installation

```python
from fc_selector.django.selector import ODataSelector, QueryBuilder

print("FC Selector installed successfully!")
```

## Compatibility verification

The CI matrix explicitly exercises these combinations on **SQLite**:

| Python | Django |
| --- | --- |
| 3.11 | 4.2.20 (declared minimum), 5.0.x, 5.2.x |
| 3.12 | 5.2.x, 6.0.x |
| 3.13 | 6.0.x |

These are compatibility tests, not recommendations to deploy older framework
versions. The quality job uses the frozen lock; test jobs override Django in
isolated environments without changing it. Pytest retains the configured
`--no-migrations` option.

PostgreSQL is not currently verified by this matrix. Add backend integration
coverage when a consumer requires it; do not infer PostgreSQL coverage from
SQLite results. SQLAlchemy support is planned but not implemented.

To reproduce one combination (with the relevant Python available):

```bash
uv run --frozen --isolated --python 3.12 --with 'django==6.0.*' \
  pytest tests/ --ignore=tests/performance/ --benchmark-disable
```

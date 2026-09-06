# Installation

## Requirements

- Python 3.11+
- Django 4.2+ and Django REST Framework 3.12+ — only for the `django` extra

## Install

For use with Django:

```bash
pip install "fc-selector[django]"
```

Or with uv:

```bash
uv add "fc-selector[django]"
```

### Without Django

The core (AST, `QueryIntent`, fluent filters, DTOs and the OData parser) is
framework-agnostic. Install the base package to parse OData queries without
pulling in Django or DRF:

```bash
pip install fc-selector
```

```python
from fc_selector.protocols.odata import parse_odata_query

intent = parse_odata_query("$filter=status eq 'published'&$top=10")
```

Everything under `fc_selector.django` requires the `django` extra.

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

`drf-spectacular` comes with the `django` extra. To document the OData
parameters in your OpenAPI/Swagger schema:

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
pip install -e ".[django]"
```

## Verify Installation

```python
from fc_selector.django.selector import ODataSelector, QueryBuilder

print("FC Selector installed successfully!")
```

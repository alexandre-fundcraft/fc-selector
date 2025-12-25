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
git clone https://github.com/fundcraft/fc-selector.git
cd fc-selector
pip install -e ".[dev]"
```

## Verify Installation

```python
from fc_selector.django.selector import ODataSelector, QueryBuilder

print("FC Selector installed successfully!")
```

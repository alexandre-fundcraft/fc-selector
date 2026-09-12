"""Run in a fresh interpreter so imported pytest/Django modules cannot hide coupling."""

import subprocess
import sys
import textwrap

import pytest


@pytest.mark.parametrize(
    "blocked,body",
    [
        (
            ("django", "sqlalchemy", "fc_selector.protocols"),
            """
from dataclasses import dataclass
from types import SimpleNamespace
from fc_selector.core import QueryBuilder
from fc_selector.core.filters import Expand, Field, OrderBy
from fc_selector.core.dtos import BaseODataDTO, UNSET
from fc_selector.core.intent import QueryIntent, ExpandIntent, SelectIntent
intent = QueryBuilder().where(Field('value').gt(1)).expand(Expand('children').select('name')).orderby(OrderBy('value')).build()
assert intent.filter.ast is not None
@dataclass
class Child(BaseODataDTO):
    name: str = UNSET
@dataclass
class Parent(BaseODataDTO):
    children: list[Child] = UNSET
    label: str = UNSET
obj = SimpleNamespace(label='root', children=[SimpleNamespace(name='child')])
projection = QueryIntent(expand=ExpandIntent({'children': QueryIntent(select=SelectIntent(['name']))}))
assert Parent.from_object(obj, projection).to_dict() == {'label': 'root', 'children': [{'name': 'child'}]}
assert Parent.from_object({'label': 'root', 'children': [{'name': 'child'}]}, projection).to_dict() == {'label': 'root', 'children': [{'name': 'child'}]}
""",
        ),
        (
            ("django", "sqlalchemy"),
            """
from fc_selector.protocols.odata import parse_odata_query
assert parse_odata_query('$filter=value gt 1&$expand=children($select=name)').expand is not None
""",
        ),
        (
            ("fc_selector.protocols", "rest_framework", "sqlalchemy"),
            """
from django.conf import settings
settings.configure(INSTALLED_APPS=[], DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}})
import django
django.setup()
from django.db import models, connection
from dataclasses import dataclass
from fc_selector.core import QueryBuilder
from fc_selector.core.filters import Field
from fc_selector.core.dtos import BaseODataDTO, UNSET
from fc_selector.django.executor import DjangoExecutor
class Row(models.Model):
    value = models.IntegerField()
    class Meta:
        app_label = 'boundary'
@dataclass
class RowDTO(BaseODataDTO):
    value: int = UNSET
with connection.schema_editor() as editor:
    editor.create_model(Row)
Row.objects.create(value=2)
intent = QueryBuilder().where(Field('value').ne(1)).select('value').build()
result = DjangoExecutor().materialize(Row.objects.all(), intent, RowDTO, as_dicts=True)
assert result == [{'value': 2}]
""",
        ),
    ],
)
def test_import_boundaries(blocked, body):
    script = f"""
import importlib.abc
import sys
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if any(fullname == prefix or fullname.startswith(prefix + '.') for prefix in {blocked!r}):
            raise AssertionError('Forbidden dependency: ' + fullname)
sys.meta_path.insert(0, Block())
""" + textwrap.dedent(body)
    result = subprocess.run([sys.executable, "-c", script], text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr

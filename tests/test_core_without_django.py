"""The [django] extra is a real boundary, not a convention.

fc_selector.core and fc_selector.protocols must import and work with Django
absent, so that `pip install fc-selector` (without the django extra) is usable.
"""

import importlib.util
import subprocess
import sys
import textwrap
import tomllib
from pathlib import Path

PROBE = textwrap.dedent(
    """
    import sys

    class _Blocked:
        \"\"\"Make django/rest_framework look uninstalled to everything downstream.\"\"\"

        def find_spec(self, name, path=None, target=None):
            root = name.split(".")[0]
            if root in {"django", "rest_framework", "drf_spectacular"}:
                raise ImportError(f"{name} is blocked by this test")
            return None

    sys.meta_path.insert(0, _Blocked())

    from fc_selector.core import QueryBuilder
    from dataclasses import dataclass
    from fc_selector.core.dtos import BaseODataDTO, UNSET
    @dataclass
    class DTO(BaseODataDTO):
        name: str = UNSET
    assert DTO.from_object({'name': 'standalone'}).to_dict() == {'name': 'standalone'}
    from fc_selector.core.filters import Field
    from fc_selector.protocols.odata import parse_odata_query

    # Import alone is a weak check: exercise the parser and the builder too.
    intent = parse_odata_query("$filter=status eq 'x'&$select=id&$expand=author&$top=5")
    assert intent.filter.ast is not None
    assert intent.select.fields == ["id"]
    assert list(intent.expand.relations) == ["author"]
    assert intent.pagination.limit == 5

    assert QueryBuilder().where(Field("a").eq(1)).top(3).build().pagination.limit == 3

    assert "django" not in sys.modules
    """
)


def test_core_and_protocols_work_without_django():
    result = subprocess.run(
        [sys.executable, "-c", PROBE],
        capture_output=True,
        text=True,
        cwd=sys.path[0] or ".",
        check=False,  # the assertion below reports stderr on failure
    )
    assert result.returncode == 0, f"core requires Django:\n{result.stderr}"


def test_optional_dependency_metadata():
    config = tomllib.loads((Path(__file__).resolve().parents[1] / "pyproject.toml").read_text())
    project = config["project"]
    assert project["dependencies"] == ["sly>=0.5"]
    extra = project["optional-dependencies"]["django"]
    assert {requirement.split(">=")[0] for requirement in extra} == {"django", "djangorestframework", "drf-spectacular"}
    dev = config["dependency-groups"]["dev"]
    assert set(extra) <= set(dev)
    assert not any(isinstance(item, str) and item.startswith("fc-selector") for item in dev)


def test_guard_rejects_each_adapter_package():
    for package in ("django", "rest_framework", "drf_spectacular"):
        result = subprocess.run(
            [sys.executable, "-c", PROBE + f"\nimport {package}"], capture_output=True, text=True, check=False
        )
        assert result.returncode != 0
        assert f"{package} is blocked by this test" in result.stderr


if __name__ == "__main__":
    # Run with python -I after installing only the built wheel (no project/dev deps).
    for package in ("django", "rest_framework", "drf_spectacular"):
        assert importlib.util.find_spec(package) is None, package
    exec(PROBE)
    print("Standalone wheel probe passed")

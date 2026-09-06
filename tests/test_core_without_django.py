"""The [django] extra is a real boundary, not a convention.

fc_selector.core and fc_selector.protocols must import and work with Django
absent, so that `pip install fc-selector` (without the django extra) is usable.
"""

import subprocess
import sys
import textwrap

PROBE = textwrap.dedent(
    """
    import sys

    class _Blocked:
        \"\"\"Make django/rest_framework look uninstalled to everything downstream.\"\"\"

        def find_spec(self, name, path=None, target=None):
            root = name.split(".")[0]
            if root in {"django", "rest_framework"}:
                raise ImportError(f"{name} is blocked by this test")
            return None

    sys.meta_path.insert(0, _Blocked())

    from fc_selector.core import QueryBuilder
    from fc_selector.core.dtos import BaseODataDTO  # noqa: F401
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

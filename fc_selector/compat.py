"""Lazy compatibility entry points; neutral core operations never call these.

Existing string-builder and model-conversion APIs remain available without
making importing the core load a protocol parser or an ORM.
"""

from typing import Any


def __getattr__(name: str) -> Any:
    if name in {
        "dto_options",
        "populate_query_builder",
        "parse_filter",
        "parse_builder_options",
        "builder_to_params",
        "builder_to_query_string",
        "parse_nested_options",
    }:
        from fc_selector.protocols.odata import builder  # noqa: PLC0415

        return getattr(builder, name)
    if name == "from_model":
        from fc_selector.django.projection import from_model  # noqa: PLC0415

        return from_model
    if name == "odata_path_to_django":
        from fc_selector.django.utils.paths import odata_path_to_django  # noqa: PLC0415

        return odata_path_to_django
    raise AttributeError(name)

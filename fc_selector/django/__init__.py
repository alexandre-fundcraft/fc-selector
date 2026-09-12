"""Django adapter public exports, loaded only when requested.

Importing a stateless adapter utility must not initialize views or DRF settings.
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .query import apply_odata_query_params
    from .selector import ODataSelector
    from .views import ODataMetadataRegistry, ODataMetadataView, ODataServiceDocumentView

__all__ = [
    "apply_odata_query_params",
    "ODataSelector",
    "ODataMetadataView",
    "ODataServiceDocumentView",
    "ODataMetadataRegistry",
]


def __getattr__(name: str) -> Any:
    if name == "apply_odata_query_params":
        from .query import apply_odata_query_params

        return apply_odata_query_params
    if name == "ODataSelector":
        from .selector import ODataSelector

        return ODataSelector
    if name in {"ODataMetadataRegistry", "ODataMetadataView", "ODataServiceDocumentView"}:
        from . import views

        return getattr(views, name)
    raise AttributeError(name)

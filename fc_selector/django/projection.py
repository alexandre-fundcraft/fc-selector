"""Django extraction for neutral DTO projection; ORM conventions live here."""

import logging

from fc_selector.core.dtos.base import UNSET, read_value

logger = logging.getLogger(__name__)


def read_model_value(instance, path, many=None):
    if many is not None:
        prefetched = getattr(instance, f"_odata_{path}", UNSET)
        if prefetched is not UNSET:
            return prefetched
        cache = getattr(instance, "_prefetched_objects_cache", {})
        if path in cache:
            return cache[path]
    value = read_value(instance, path.replace("__", ".").replace("/", "."))
    if value is not UNSET and callable(getattr(value, "all", None)):
        if many:
            logger.debug(
                "Potential N+1 query: '%s' not prefetched for %s. Consider using prefetch_related().",
                path,
                instance.__class__.__name__,
            )
            return value.all()
        return UNSET
    return value


def from_model(
    dto_class,
    instance,
    selected_fields=None,
    expanded_fields=None,
    expand_options=None,
    field_mapping=None,
    *,
    _depth=0,
):
    from fc_selector.protocols.odata.builder import projection_intent

    intent = projection_intent(selected_fields, expanded_fields, expand_options, depth=_depth)
    return dto_class.from_object(instance, intent, field_mapping, value_reader=read_model_value, _depth=_depth)

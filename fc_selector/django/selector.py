"""
OData Selector

Selector layer for executing OData queries on Django models.
Provides a clean interface for using OData queries in selectors,
use cases, and any code that needs QuerySets.
"""

from typing import TYPE_CHECKING

from django.db.models import QuerySet

from .core import apply_odata_to_queryset

if TYPE_CHECKING:
    pass


class ODataSelector:
    """
    Selector for executing OData queries on Django models.

    Provides a clean interface for using OData queries in selectors,
    use cases, and any code that needs QuerySets. This class leverages
    the existing odata-query library for parsing and filtering, combined
    with custom optimization logic for field selection and eager loading.

    Examples:
        >>> # Basic usage
        >>> selector = ODataSelector(BlogPost)
        >>> posts = selector.query("$filter=status eq 'published'&$expand=author")

        >>> # With business logic
        >>> base_qs = BlogPost.objects.filter(featured=True)
        >>> posts = selector.query("$filter=rating gt 4.0", base_queryset=base_qs)

        >>> # Helper methods
        >>> count = selector.count("$filter=status eq 'published'")
        >>> exists = selector.exists("$filter=title eq 'My Post'")
        >>> first_post = selector.first("$orderby=created_at desc")
    """

    def __init__(self, model_class=None):
        """
        Initialize selector.

        Args:
            model_class: Optional Django model. Can be set per-query if not provided.
        """
        self.model = model_class

    def query(
        self, query_string: str = None, model_class=None, base_queryset: QuerySet = None
    ) -> QuerySet:
        """
        Execute OData query and return QuerySet.

        Args:
            query_string: OData query string (e.g., "$filter=status eq 'published'&$expand=author")
            model_class: Django model (overrides __init__ value)
            base_queryset: Optional base QuerySet to filter (default: Model.objects.all())

        Returns:
            Optimized Django QuerySet

        Examples:
            >>> selector = ODataSelector(BlogPost)
            >>> posts = selector.query("$filter=status eq 'published'&$expand=author")

            >>> # With custom base queryset
            >>> posts = selector.query(
            ...     "$filter=rating gt 4.0",
            ...     base_queryset=BlogPost.objects.filter(featured=True)
            ... )
        """
        model = model_class or self.model
        if not model:
            raise ValueError("model_class required")

        # Get base queryset
        if base_queryset is None:
            base_queryset = model.objects.all()

        # Apply OData query using the core wrapper
        return apply_odata_to_queryset(base_queryset, query_string)

    def query_from_request(
        self, request, model_class=None, base_queryset: QuerySet = None
    ) -> QuerySet:
        """
        Query from Django/DRF request.

        Args:
            request: Django/DRF request object
            model_class: Django model (overrides __init__ value)
            base_queryset: Optional base QuerySet to filter

        Returns:
            Optimized Django QuerySet
        """
        query_string = request.META.get("QUERY_STRING", "")
        return self.query(query_string, model_class, base_queryset)

    def count(self, query_string: str, model_class=None) -> int:
        """
        Get count of matching records.

        Args:
            query_string: OData query string
            model_class: Django model (overrides __init__ value)

        Returns:
            Count of matching records

        Example:
            >>> selector = ODataSelector(BlogPost)
            >>> published_count = selector.count("$filter=status eq 'published'")
        """
        qs = self.query(query_string, model_class)
        return qs.count()

    def exists(self, query_string: str, model_class=None) -> bool:
        """
        Check if any records match.

        Args:
            query_string: OData query string
            model_class: Django model (overrides __init__ value)

        Returns:
            True if any records match, False otherwise

        Example:
            >>> selector = ODataSelector(BlogPost)
            >>> has_drafts = selector.exists("$filter=status eq 'draft'")
        """
        qs = self.query(query_string, model_class)
        return qs.exists()

    def first(self, query_string: str, model_class=None):
        """
        Get first matching record.

        Args:
            query_string: OData query string
            model_class: Django model (overrides __init__ value)

        Returns:
            First matching record or None

        Example:
            >>> selector = ODataSelector(BlogPost)
            >>> latest_post = selector.first("$orderby=created_at desc")
        """
        qs = self.query(query_string, model_class)
        return qs.first()

    def get_list(
        self, query_string: str = None, model_class=None, base_queryset: QuerySet = None
    ) -> list:
        """
        Get evaluated list of objects.

        Args:
            query_string: OData query string
            model_class: Django model (overrides __init__ value)
            base_queryset: Optional base QuerySet to filter

        Returns:
            List of model instances

        Example:
            >>> selector = ODataSelector(BlogPost)
            >>> posts_list = selector.get_list("$filter=status eq 'published'&$top=10")
        """
        return list(self.query(query_string, model_class, base_queryset))

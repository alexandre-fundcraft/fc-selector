"""
OData Selector for Django models.

Provides a clean selector interface for executing OData queries on Django models.
"""

import re
from typing import TYPE_CHECKING, Any, Optional

from django.db.models import QuerySet

from fc_selector.core.query_builder import ODataQueryBuilder
from fc_selector.django.query import apply_odata_query_params

if TYPE_CHECKING:
    from django.db.models import Model


class ODataSelector:
    """
    Selector for executing OData queries on Django models.

    Provides a clean interface for using OData queries in selectors,
    use cases, and any code that needs QuerySets.

    Supports Meta class configuration for:
    - Model specification
    - DTO class (for automatic model-to-DTO conversion)
    - Expandable fields (for nested DTOs)

    Examples:
        >>> # Basic usage (backward compatible)
        >>> selector = ODataSelector(BlogPost)
        >>> posts = selector.query("$filter=status eq 'published'&$expand=author")

        >>> # With Meta class (new style)
        >>> class BlogPostSelector(ODataSelector):
        ...     class Meta:
        ...         model = BlogPost
        ...         dto_class = BlogPostDTO
        ...         expandable_fields = {
        ...             'author': AuthorDTO,
        ...         }
        ...
        ...     def get_queryset(self):
        ...         # Override to add custom filtering
        ...         return BlogPost.objects.filter(published=True)

        >>> # Helper methods
        >>> count = selector.count("$filter=status eq 'published'")
        >>> exists = selector.exists("$filter=title eq 'My Post'")
        >>> first_post = selector.first("$orderby=created_at desc")
    """

    def __init__(self, model_class: Optional["Model"] = None):
        """
        Initialize selector.

        Args:
            model_class: Optional Django model. Can be set per-query if not provided.
                        If Meta class is defined, it will take precedence.
        """
        # Check for Meta class configuration first
        if hasattr(self.__class__, 'Meta'):
            self.model = getattr(self.__class__.Meta, 'model', model_class)
            self.dto_class = getattr(self.__class__.Meta, 'dto_class', None)
            self.expandable_fields = getattr(self.__class__.Meta, 'expandable_fields', {})
            self.field_aliases = getattr(self.__class__.Meta, 'field_aliases', {})
        else:
            # Backward compatibility: use passed model_class
            self.model = model_class
            self.dto_class = None
            self.expandable_fields = {}
            self.field_aliases = {}

        # Build reverse alias map for output (internal_name -> alias_name)
        self._reverse_aliases: dict[str, str] = {v: k for k, v in self.field_aliases.items()}

    # ==================== Alias Resolution ====================

    def _resolve_alias(self, field_name: str) -> str:
        """
        Resolve a field alias to its internal field name.

        Args:
            field_name: Field name (possibly an alias)

        Returns:
            Internal field name (e.g., 'authorName' -> 'author__username')
        """
        return self.field_aliases.get(field_name, field_name)

    def _resolve_alias_reverse(self, internal_name: str) -> str:
        """
        Resolve an internal field name to its alias (for output).

        Args:
            internal_name: Internal field name (e.g., 'author__username')

        Returns:
            Alias name (e.g., 'authorName') or original if no alias
        """
        return self._reverse_aliases.get(internal_name, internal_name)

    def _resolve_aliases_in_select(self, select_value: str) -> str:
        """
        Resolve aliases in a $select parameter value.

        Args:
            select_value: Comma-separated field names (e.g., 'id,authorName,createdAt')

        Returns:
            Resolved field names (e.g., 'id,author__username,created_at')
        """
        if not select_value or not self.field_aliases:
            return select_value

        fields = [f.strip() for f in select_value.split(',')]
        resolved = [self._resolve_alias(f) for f in fields]
        return ','.join(resolved)

    def _resolve_aliases_in_filter(self, filter_value: str) -> str:
        """
        Resolve aliases in a $filter expression.

        Args:
            filter_value: OData filter expression (e.g., "authorName eq 'john'")

        Returns:
            Resolved filter expression (e.g., "author__username eq 'john'")
        """
        if not filter_value or not self.field_aliases:
            return filter_value

        result = filter_value

        # Sort aliases by length (longest first) to avoid partial replacements
        sorted_aliases = sorted(self.field_aliases.keys(), key=len, reverse=True)

        for alias in sorted_aliases:
            internal = self.field_aliases[alias]
            # Use word boundary matching to avoid partial replacements
            # Match alias that's not part of a larger word and not inside quotes
            pattern = r'\b' + re.escape(alias) + r'\b(?=(?:[^\']*\'[^\']*\')*[^\']*$)'
            result = re.sub(pattern, internal, result)

        return result

    def _resolve_aliases_in_orderby(self, orderby_value: str) -> str:
        """
        Resolve aliases in a $orderby parameter value.

        Args:
            orderby_value: Order by expression (e.g., 'authorName desc,createdAt asc')

        Returns:
            Resolved order by (e.g., 'author__username desc,created_at asc')
        """
        if not orderby_value or not self.field_aliases:
            return orderby_value

        parts = [p.strip() for p in orderby_value.split(',')]
        resolved_parts = []

        for part in parts:
            # Split field and direction (e.g., 'authorName desc' -> ['authorName', 'desc'])
            tokens = part.split()
            if tokens:
                field = self._resolve_alias(tokens[0])
                direction = tokens[1] if len(tokens) > 1 else ''
                resolved_parts.append(f"{field} {direction}".strip())

        return ','.join(resolved_parts)

    def _resolve_aliases_in_query_string(self, query_string: str) -> str:
        """
        Resolve all aliases in an OData query string.

        Args:
            query_string: Full OData query string

        Returns:
            Query string with all aliases resolved to internal field names
        """
        if not query_string or not self.field_aliases:
            return query_string

        # Parse query string into parameters
        from urllib.parse import unquote_plus

        # Handle both encoded and non-encoded query strings
        if "%" in query_string or "+" in query_string:
            query_string = unquote_plus(query_string)

        params = {}
        for param in query_string.split('&'):
            if '=' in param:
                key, value = param.split('=', 1)
                params[key] = value

        # Resolve aliases in each relevant parameter
        if '$select' in params:
            params['$select'] = self._resolve_aliases_in_select(params['$select'])

        if '$filter' in params:
            params['$filter'] = self._resolve_aliases_in_filter(params['$filter'])

        if '$orderby' in params:
            params['$orderby'] = self._resolve_aliases_in_orderby(params['$orderby'])

        # Rebuild query string
        return '&'.join(f"{k}={v}" for k, v in params.items())

    def _get_related_fields_from_aliases(self, fields: list[str]) -> set[str]:
        """
        Extract related field names for select_related from alias definitions.

        Args:
            fields: List of field names (may include aliases)

        Returns:
            Set of related field names (e.g., {'author', 'categories'})
        """
        related = set()
        for field in fields:
            resolved = self._resolve_alias(field)
            if '__' in resolved:
                # 'author__username' -> 'author'
                related.add(resolved.split('__')[0])
        return related

    def get_queryset(self) -> QuerySet:
        """
        Get base queryset for this selector.

        Override this method to add custom filtering, prefetching, or other
        query modifications that should always apply.

        Returns:
            Base QuerySet

        Example:
            >>> class BlogPostSelector(ODataSelector):
            ...     class Meta:
            ...         model = BlogPost
            ...
            ...     def get_queryset(self):
            ...         # Only return published posts by default
            ...         return BlogPost.objects.filter(status='published')
        """
        if not self.model:
            raise ValueError("model not configured. Set it in Meta class or pass to __init__")

        qs = self.model.objects.all()

        # Auto-detect OneToOne fields and select_related them
        # This avoids N+1 for profile-like models (e.g. Author -> User)
        try:
            from django.db.models import OneToOneField
            select_related_fields = []
            for field in self.model._meta.fields:
                if isinstance(field, OneToOneField):
                    select_related_fields.append(field.name)

            if select_related_fields:
                qs = qs.select_related(*select_related_fields)
        except Exception:
            pass

        return qs

    def query(
        self,
        query_string: str = None,
        model_class: Optional["Model"] = None,
        base_queryset: QuerySet | None = None,
    ) -> QuerySet:
        """
        Execute OData query and return QuerySet.

        Args:
            query_string: OData query string (e.g., "$filter=status eq 'published'&$expand=author")
            model_class: Django model (overrides __init__ value)
            base_queryset: Optional base QuerySet to filter (default: self.get_queryset())

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
            base_queryset = self.get_queryset()

        # Parse and apply OData query
        if not query_string:
            return base_queryset

        # Resolve field aliases before processing
        query_string = self._resolve_aliases_in_query_string(query_string)

        # Auto select_related for alias fields that reference related models
        if self.field_aliases:
            related_fields = self._get_related_fields_from_aliases(
                list(self.field_aliases.values())
            )
            if related_fields:
                # Only add select_related for FK/O2O fields that exist
                from django.db.models import ForeignKey, OneToOneField
                valid_related = []
                for field_name in related_fields:
                    try:
                        field = model._meta.get_field(field_name)
                        if isinstance(field, (ForeignKey, OneToOneField)):
                            valid_related.append(field_name)
                    except Exception:
                        pass
                if valid_related:
                    base_queryset = base_queryset.select_related(*valid_related)

        from fc_selector.core.parsers.query import parse_odata_query

        query_params = parse_odata_query(query_string)

        # Apply field selection optimization with only()
        # Only apply if there's an explicit $select
        if query_params.select and hasattr(query_params.select, 'fields') and query_params.select.fields:
            base_queryset = self._optimize_queryset_for_select(
                base_queryset, query_params.select, query_params.expand, model
            )

        # Apply query optimization based on $expand
        if query_params.expand:
            base_queryset = self._optimize_queryset_for_expand(
                base_queryset, query_params.expand, model
            )

        return apply_odata_query_params(base_queryset, query_params.to_dict())

    def _optimize_queryset_for_select(
        self, queryset: QuerySet, select_param, expand_param, model: "Model"
    ) -> QuerySet:
        """
        Optimize queryset by using only() to limit fetched fields.

        Args:
            queryset: Base queryset to optimize
            select_param: Parsed select parameter
            expand_param: Parsed expand parameter (to include expanded field keys)
            model: Django model class

        Returns:
            Optimized queryset with only() applied
        """
        # Get selected field names
        selected_fields = set(select_param.fields) if hasattr(select_param, 'fields') else set()

        if not selected_fields:
            return queryset

        # Build the list of fields to fetch
        fields_to_fetch = []

        # Always include the primary key
        fields_to_fetch.append('pk')

        # Add selected fields from the main model
        for field_name in selected_fields:
            try:
                # Check if field exists on the model
                model._meta.get_field(field_name)
                fields_to_fetch.append(field_name)
            except Exception:
                # Field might be a property or doesn't exist
                pass

        # Add foreign key fields for expanded relationships
        if expand_param and hasattr(expand_param, 'nested_options'):
            expand_fields = expand_param.nested_options
            for field_name, nested_opts in expand_fields.items():
                try:
                    field = model._meta.get_field(field_name)
                    from django.db.models import ForeignKey, OneToOneField

                    if isinstance(field, (ForeignKey, OneToOneField)):
                        # Add the FK field itself (e.g., 'author')
                        if field_name not in fields_to_fetch:
                            fields_to_fetch.append(field_name)

                        # Parse nested $select to add specific fields from related model
                        if nested_opts and '$select' in nested_opts:
                            nested_fields = nested_opts['$select'].split(',')
                            for nested_field in nested_fields:
                                nested_field = nested_field.strip()
                                # Check if the nested field exists as a real database field
                                try:
                                    field.related_model._meta.get_field(nested_field)
                                    # Add as author__field_name
                                    related_field_path = f"{field_name}__{nested_field}"
                                    fields_to_fetch.append(related_field_path)
                                except Exception:
                                    # Skip properties and non-existent fields
                                    pass

                                # Check for further nesting
                                if '$expand' in nested_opts:
                                    # Parse nested expand to get deeper fields
                                    nested_expand_fields = self._parse_nested_select_fields(
                                        field_name, nested_opts, field.related_model
                                    )
                                    fields_to_fetch.extend(nested_expand_fields)
                        else:
                            # No nested $select, but we need to add all fields for the related model
                            # This will be handled by select_related, but we should still limit
                            pass

                except Exception:
                    pass

        # Apply only() if we have fields to fetch
        if fields_to_fetch:
            try:
                queryset = queryset.only(*fields_to_fetch)
            except Exception:
                # If only() fails, continue without it
                pass

        return queryset

    def _parse_nested_select_fields(
        self, parent_field: str, nested_opts: dict, related_model: "Model"
    ) -> list[str]:
        """
        Parse nested select fields for expanded relationships.

        Args:
            parent_field: Parent field name (e.g., "author")
            nested_opts: Nested options dict (e.g., {'$select': 'name', '$expand': 'user'})
            related_model: Related model class

        Returns:
            List of field paths (e.g., ["author__user__id", "author__user__username"])
        """
        fields = []

        if '$expand' in nested_opts:
            expand_value = nested_opts['$expand']

            # Parse the nested expand
            from fc_selector.core.parsers.query import parse_odata_query

            try:
                query = f'$expand={expand_value}'
                query_params = parse_odata_query(query)

                if query_params.expand and hasattr(query_params.expand, 'nested_options'):
                    for nested_field_name, further_opts in query_params.expand.nested_options.items():
                        try:
                            nested_field = related_model._meta.get_field(nested_field_name)
                            from django.db.models import ForeignKey, OneToOneField

                            if isinstance(nested_field, (ForeignKey, OneToOneField)):
                                # Add the FK field
                                nested_path = f"{parent_field}__{nested_field_name}"

                                # Check if there's a nested $select
                                if further_opts and '$select' in further_opts:
                                    further_fields = further_opts['$select'].split(',')
                                    for further_field in further_fields:
                                        further_field = further_field.strip()
                                        # Check if field exists as a real database field
                                        try:
                                            nested_field.related_model._meta.get_field(further_field)
                                            field_path = f"{nested_path}__{further_field}"
                                            fields.append(field_path)
                                        except Exception:
                                            # Skip properties
                                            pass

                                        # Recurse for even deeper nesting
                                        if '$expand' in further_opts:
                                            deeper_fields = self._parse_nested_select_fields(
                                                nested_path,
                                                further_opts,
                                                nested_field.related_model
                                            )
                                            fields.extend(deeper_fields)
                        except Exception:
                            pass

            except Exception:
                pass

        return fields

    def _optimize_queryset_for_expand(
        self, queryset: QuerySet, expand_param, model: "Model"
    ) -> QuerySet:
        """
        Optimize queryset by adding select_related/prefetch_related based on $expand.

        Args:
            queryset: Base queryset to optimize
            expand_param: Parsed expand parameter
            model: Django model class

        Returns:
            Optimized queryset with select_related/prefetch_related
        """
        from django.db.models import ForeignKey, ManyToManyField, OneToOneField

        # Get expand options (field names and nested options)
        if hasattr(expand_param, 'nested_options'):
            expand_fields = expand_param.nested_options
        else:
            # Fallback to simple field list
            expand_fields = {}
            if hasattr(expand_param, 'fields'):
                for field in expand_param.fields:
                    expand_fields[field] = {}

        if not expand_fields:
            return queryset

        select_related_fields = []
        prefetch_related_fields = []

        # Analyze each expanded field
        for field_name, nested_opts in expand_fields.items():
            try:
                # Get the field from the model
                field = model._meta.get_field(field_name)

                # Determine relationship type
                if isinstance(field, (ForeignKey, OneToOneField)):
                    # Use select_related for FK and O2O
                    # Handle nested expands recursively
                    if nested_opts and '$expand' in nested_opts:
                        # Parse nested expand
                        nested_expand_fields = self._parse_nested_expand(
                            field_name, nested_opts['$expand'], field.related_model
                        )
                        select_related_fields.extend(nested_expand_fields)
                    else:
                        select_related_fields.append(field_name)

                elif isinstance(field, ManyToManyField) or hasattr(field, 'get_accessor_name'):
                    # Use prefetch_related for M2M and reverse FK
                    # For now, just add the field name
                    # TODO: Handle nested prefetches with Prefetch objects
                    prefetch_related_fields.append(field_name)

            except Exception:
                # Field might not exist or be a reverse relation
                # Try to handle reverse relations
                try:
                    # Check if it's a reverse relation
                    related_objects = model._meta.related_objects
                    for rel in related_objects:
                        if rel.get_accessor_name() == field_name:
                            prefetch_related_fields.append(field_name)
                            break
                except Exception:
                    # Skip fields we can't optimize
                    pass

        # Apply optimizations
        if select_related_fields:
            queryset = queryset.select_related(*select_related_fields)

        if prefetch_related_fields:
            queryset = queryset.prefetch_related(*prefetch_related_fields)

        return queryset

    def _parse_nested_expand(
        self, parent_field: str, nested_expand_str: str, related_model: "Model"
    ) -> list[str]:
        """
        Parse nested expand options and build select_related paths.

        Args:
            parent_field: Parent field name
            nested_expand_str: Nested expand string (e.g., "user($select=username)")
            related_model: Related model class

        Returns:
            List of select_related paths (e.g., ["author__user"])
        """
        from django.db.models import ForeignKey, OneToOneField

        # Parse the nested expand
        from fc_selector.core.parsers.query import parse_odata_query

        try:
            query = f'$expand={nested_expand_str}'
            query_params = parse_odata_query(query)

            if not query_params.expand:
                return [parent_field]

            # Get nested field names
            if hasattr(query_params.expand, 'nested_options'):
                nested_fields = query_params.expand.nested_options
            else:
                return [parent_field]

            paths = [parent_field]  # Always include the parent

            # Add nested paths
            for nested_field_name, nested_opts in nested_fields.items():
                try:
                    nested_field = related_model._meta.get_field(nested_field_name)

                    if isinstance(nested_field, (ForeignKey, OneToOneField)):
                        # Build the path
                        nested_path = f"{parent_field}__{nested_field_name}"

                        # Check for further nesting
                        if nested_opts and '$expand' in nested_opts:
                            further_nested = self._parse_nested_expand(
                                nested_path,
                                nested_opts['$expand'],
                                nested_field.related_model
                            )
                            paths.extend(further_nested)
                        else:
                            paths.append(nested_path)
                except Exception:
                    pass

            return paths

        except Exception:
            # If parsing fails, just return the parent field
            return [parent_field]

    def _extract_selected_fields(self, query_string: str | None) -> set[str] | None:
        """
        Extract selected fields from $select parameter.

        Args:
            query_string: OData query string

        Returns:
            Set of selected field names, or None if no $select specified
        """
        if not query_string:
            return None

        from fc_selector.core.parsers.query import parse_odata_query

        query_params = parse_odata_query(query_string)
        if hasattr(query_params, 'select') and query_params.select:
            return set(query_params.select.fields)
        return None

    def _extract_expanded_fields(self, query_string: str | None) -> set[str]:
        """
        Extract expanded fields from $expand parameter.

        Args:
            query_string: OData query string

        Returns:
            Set of expanded field names
        """
        if not query_string:
            return set()

        from fc_selector.core.parsers.query import parse_odata_query

        query_params = parse_odata_query(query_string)
        if hasattr(query_params, 'expand') and query_params.expand:
            expanded_fields = set()

            # Get fields with options (e.g., author($select=id))
            if hasattr(query_params.expand, 'nested_options'):
                expanded_fields.update(query_params.expand.nested_options.keys())

            # Also get simple expand fields without options (e.g., categories)
            if hasattr(query_params.expand, 'value') and isinstance(query_params.expand.value, str):
                # Split by semicolon to get individual expand fields
                expand_parts = [part.strip() for part in query_params.expand.value.split(';')]
                for part in expand_parts:
                    # Extract field name (before any parenthesis)
                    field_name = part.split('(')[0].strip()
                    if field_name:
                        expanded_fields.add(field_name)

            return expanded_fields
        return set()

    def _extract_expand_options(self, query_string: str | None) -> dict:
        """
        Extract expanded fields with their nested options from $expand parameter.

        Args:
            query_string: OData query string

        Returns:
            Dictionary mapping field names to their nested options
            Example: {'author': {'$select': 'name,email'}, 'categories': {}}
        """
        if not query_string:
            return {}

        from fc_selector.core.parsers.query import parse_odata_query

        query_params = parse_odata_query(query_string)
        if hasattr(query_params, 'expand') and query_params.expand:
            # Get nested options (fields with options like author($select=id))
            expand_options = {}
            if hasattr(query_params.expand, 'nested_options'):
                expand_options = dict(query_params.expand.nested_options)

            # Also check for simple expand fields without options (e.g., categories)
            # Parse the raw $expand value to get all fields
            if hasattr(query_params.expand, 'value') and isinstance(query_params.expand.value, str):
                # Split by semicolon to get individual expand fields
                expand_parts = [part.strip() for part in query_params.expand.value.split(';')]
                for part in expand_parts:
                    # Extract field name (before any parenthesis)
                    field_name = part.split('(')[0].strip()
                    if field_name and field_name not in expand_options:
                        # Add field with empty options
                        expand_options[field_name] = {}

            return expand_options
        return {}

    def to_dto(self, instance: "Model", selected_fields: set[str] | None = None,
               expanded_fields: set[str] | None = None, expand_options: dict | None = None) -> Any:
        """
        Convert model instance to DTO.

        Args:
            instance: Model instance to convert
            selected_fields: Fields selected via $select
            expanded_fields: Fields expanded via $expand
            expand_options: Nested options for expanded fields (e.g., {'author': {'$select': 'name'}})

        Returns:
            DTO instance

        Raises:
            ValueError: If dto_class is not configured
        """
        if not self.dto_class:
            raise ValueError("dto_class not configured in Meta")

        return self.dto_class.from_model(instance, selected_fields, expanded_fields, expand_options)

    def to_dtos(self, instances: list["Model"], selected_fields: set[str] | None = None,
                expanded_fields: set[str] | None = None, expand_options: dict | None = None) -> list[Any]:
        """
        Convert multiple model instances to DTOs.

        Args:
            instances: List of model instances
            selected_fields: Fields selected via $select
            expanded_fields: Fields expanded via $expand
            expand_options: Nested options for expanded fields

        Returns:
            List of DTO instances
        """
        return [self.to_dto(inst, selected_fields, expanded_fields, expand_options) for inst in instances]

    def query_as_dtos(
        self,
        query_string: str = None,
        model_class: Optional["Model"] = None,
        base_queryset: QuerySet | None = None,
    ) -> list[Any]:
        """
        Execute OData query and return list of DTOs.

        Args:
            query_string: OData query string
            model_class: Django model (overrides __init__ value)
            base_queryset: Optional base QuerySet to filter

        Returns:
            List of DTO instances with sentinel values for unselected fields

        Example:
            >>> selector = BlogPostSelector()
            >>> dtos = selector.query_as_dtos("$select=id,title&$filter=status eq 'published'")
            >>> # dtos[0].id = 1
            >>> # dtos[0].title = "My Post"
            >>> # dtos[0].content = UNSET  # Not selected
        """
        if not self.dto_class:
            raise ValueError("dto_class not configured in Meta. Cannot convert to DTOs.")

        # Get QuerySet
        queryset = self.query(query_string, model_class, base_queryset)

        # Parse OData query to extract field selections
        # Reuse the core parser instead of duplicating parsing logic
        from fc_selector.core.parsers.query import parse_odata_query

        query_params = parse_odata_query(query_string) if query_string else None

        # Extract selected fields from $select
        selected_fields = None
        if query_params and query_params.select:
            selected_fields = set(query_params.select.fields)

        # Extract expanded fields and options from $expand
        # The core parser already extracts ALL fields (both simple and with options)
        expanded_fields = set()
        expand_options = {}
        if query_params and query_params.expand:
            # nested_options contains ALL expanded fields (simple + with options)
            expand_options = dict(query_params.expand.nested_options)
            expanded_fields = set(expand_options.keys())

        # Convert to DTOs
        instances = list(queryset)
        return self.to_dtos(instances, selected_fields, expanded_fields, expand_options)

    def query_from_request(
        self,
        request,
        model_class: Optional["Model"] = None,
        base_queryset: QuerySet | None = None,
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

    def count(self, query_string: str, model_class: Optional["Model"] = None) -> int:
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

    def exists(self, query_string: str, model_class: Optional["Model"] = None) -> bool:
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

    def first(
        self, query_string: str, model_class: Optional["Model"] = None
    ) -> Optional["Model"]:
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
        self,
        query_string: str = None,
        model_class: Optional["Model"] = None,
        base_queryset: QuerySet | None = None,
    ) -> list["Model"]:
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

    # ==================== NEW API: Query Builder Methods ====================
    # These methods accept ODataQueryBuilder and return DTOs directly,
    # without exposing the persistence layer (QuerySet).

    def _apply_query_builder(
        self,
        query_builder: ODataQueryBuilder,
        base_queryset: QuerySet | None = None,
    ) -> QuerySet:
        """
        Internal method to apply ODataQueryBuilder to a queryset.

        Args:
            query_builder: ODataQueryBuilder instance
            base_queryset: Optional base QuerySet

        Returns:
            Filtered QuerySet (internal use only)
        """
        # Get base queryset
        if base_queryset is None:
            base_queryset = self.get_queryset()

        # Apply OData query string
        query_string = query_builder.build_query_string()
        if query_string:
            return self.query(query_string, base_queryset=base_queryset)

        return base_queryset

    def get_one(
        self,
        query_builder: ODataQueryBuilder,
    ) -> Any | None:
        """
        Get a single DTO matching the query.

        Args:
            query_builder: ODataQueryBuilder with OData filters

        Returns:
            DTO instance or None if not found

        Example:
            >>> selector = UserSelector()
            >>> query = ODataQueryBuilder().select('id', 'username').and_filter('id eq 5')
            >>> user_dto = selector.get_one(query)
        """
        if not self.dto_class:
            raise ValueError("dto_class not configured in Meta. Cannot convert to DTO.")

        queryset = self._apply_query_builder(query_builder)
        instance = queryset.first()

        if instance is None:
            return None

        # Extract OData options for DTO conversion
        query_string = query_builder.build_query_string()
        selected_fields = self._extract_selected_fields(query_string) if query_string else None
        expanded_fields = self._extract_expanded_fields(query_string) if query_string else set()
        expand_options = self._extract_expand_options(query_string) if query_string else {}

        return self.to_dto(instance, selected_fields, expanded_fields, expand_options)

    def get_many(
        self,
        query_builder: ODataQueryBuilder | None = None,
    ) -> list[Any]:
        """
        Get a list of DTOs matching the query.

        Args:
            query_builder: ODataQueryBuilder with OData filters (optional)

        Returns:
            List of DTO instances

        Example:
            >>> selector = BlogPostSelector()
            >>> query = ODataQueryBuilder().filter("status eq 'published'").top(10).select('id', 'title')
            >>> posts = selector.get_many(query)
        """
        if not self.dto_class:
            raise ValueError("dto_class not configured in Meta. Cannot convert to DTOs.")

        if query_builder is None:
            query_builder = ODataQueryBuilder()

        queryset = self._apply_query_builder(query_builder)
        instances = list(queryset)

        # Extract OData options for DTO conversion
        query_string = query_builder.build_query_string()
        selected_fields = self._extract_selected_fields(query_string) if query_string else None
        expanded_fields = self._extract_expanded_fields(query_string) if query_string else set()
        expand_options = self._extract_expand_options(query_string) if query_string else {}

        return self.to_dtos(instances, selected_fields, expanded_fields, expand_options)

    def get_by_pk(
        self,
        pk: Any,
        query_builder: ODataQueryBuilder | None = None,
    ) -> Any | None:
        """
        Get a single DTO by primary key.

        Convenience method that wraps get_one() with an id filter.

        Args:
            pk: Primary key value
            query_builder: Optional ODataQueryBuilder for $select/$expand

        Returns:
            DTO instance or None if not found

        Example:
            >>> selector = BlogPostSelector()
            >>> query = ODataQueryBuilder().select('id', 'title').expand('author')
            >>> post = selector.get_by_pk(1, query)
        """
        if query_builder is None:
            query_builder = ODataQueryBuilder()

        query_builder.and_filter(f"id eq {pk}")
        return self.get_one(query_builder)

    def count_by(
        self,
        query_builder: ODataQueryBuilder | None = None,
    ) -> int:
        """
        Get count of records matching the query.

        Args:
            query_builder: ODataQueryBuilder with OData filters (optional)

        Returns:
            Count of matching records

        Example:
            >>> selector = BlogPostSelector()
            >>> query = ODataQueryBuilder().filter("status eq 'published'")
            >>> count = selector.count_by(query)
        """
        if query_builder is None:
            query_builder = ODataQueryBuilder()

        queryset = self._apply_query_builder(query_builder)
        return queryset.count()

    def exists_by(
        self,
        query_builder: ODataQueryBuilder | None = None,
    ) -> bool:
        """
        Check if any records match the query.

        Args:
            query_builder: ODataQueryBuilder with OData filters (optional)

        Returns:
            True if any records match

        Example:
            >>> selector = BlogPostSelector()
            >>> query = ODataQueryBuilder().filter("slug eq 'my-post'")
            >>> exists = selector.exists_by(query)
        """
        if query_builder is None:
            query_builder = ODataQueryBuilder()

        queryset = self._apply_query_builder(query_builder)
        return queryset.exists()

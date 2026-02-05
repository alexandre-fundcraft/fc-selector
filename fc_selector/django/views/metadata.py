"""
Automatic OData metadata views.

These views generate $metadata and service document automatically
from registered ODataSelectors.
"""

from django.db import models
from django.http import HttpResponse, JsonResponse
from django.views import View

from fc_selector.django.selector import ODataSelector


class ODataMetadataRegistry:
    """
    Registry for OData entity sets.

    Selectors register themselves here to be included in $metadata.
    """

    _instance = None
    _selectors: dict[str, type[ODataSelector]] = {}
    _namespace: str = "ODataService"

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def register(cls, entity_set_name: str, selector_class: type[ODataSelector]):
        """Register a selector for an entity set."""
        cls._selectors[entity_set_name] = selector_class

    @classmethod
    def get_selectors(cls) -> dict[str, type[ODataSelector]]:
        """Get all registered selectors."""
        return cls._selectors.copy()

    @classmethod
    def set_namespace(cls, namespace: str):
        """Set the OData namespace."""
        cls._namespace = namespace

    @classmethod
    def get_namespace(cls) -> str:
        """Get the OData namespace."""
        return cls._namespace

    @classmethod
    def clear(cls):
        """Clear all registrations (useful for testing)."""
        cls._selectors = {}


# Convenience function
def register_odata_entity(entity_set_name: str):
    """
    Decorator to register an ODataSelector for metadata generation.

    Usage:
        @register_odata_entity("posts")
        class BlogPostSelector(ODataSelector):
            class Meta:
                model = BlogPost
                dto_class = BlogPostDTO
    """

    def decorator(cls):
        ODataMetadataRegistry.register(entity_set_name, cls)
        return cls

    return decorator


class ODataMetadataView(View):
    """
    OData $metadata endpoint.

    Automatically generates EDM (Entity Data Model) schema from registered selectors.

    Usage in urls.py:
        path("odata/$metadata", ODataMetadataView.as_view(), name="odata-metadata"),
    """

    def get(self, request, *args, **kwargs):
        """Generate and return OData metadata XML."""
        namespace = ODataMetadataRegistry.get_namespace()
        selectors = ODataMetadataRegistry.get_selectors()

        # Build set of registered models for filtering navigation properties
        registered_models = set()
        for selector_class in selectors.values():
            selector = selector_class()
            if selector.model:
                registered_models.add(selector.model)

        entity_types = []
        entity_sets = []
        nav_bindings = {}

        for entity_set_name, selector_class in selectors.items():
            selector = selector_class()
            model_class = selector.model
            dto_class = selector.dto_class
            expandable_fields = getattr(selector, "expandable_fields", {}) or {}

            if not model_class:
                continue

            entity_type_name = model_class.__name__
            entity_type_xml = self._generate_entity_type(
                entity_type_name,
                model_class,
                dto_class,
                namespace,
                registered_models,
                expandable_fields,
            )
            entity_types.append(entity_type_xml)

            # Collect navigation bindings (only for expandable fields)
            nav_bindings[entity_set_name] = self._get_navigation_bindings(model_class, selectors, expandable_fields)

            entity_sets.append(
                f'        <EntitySet Name="{entity_set_name}" EntityType="{namespace}.{entity_type_name}">'
            )
            for nav_prop, target in nav_bindings[entity_set_name].items():
                entity_sets.append(f'          <NavigationPropertyBinding Path="{nav_prop}" Target="{target}"/>')
            entity_sets.append("        </EntitySet>")

        # Generate Capabilities annotations
        annotations = self._generate_capabilities_annotations(selectors, namespace)

        metadata_xml = f'''<?xml version="1.0" encoding="utf-8"?>
<edmx:Edmx Version="4.0" xmlns:edmx="http://docs.oasis-open.org/odata/ns/edmx">
  <edmx:DataServices>
    <Schema Namespace="{namespace}" xmlns="http://docs.oasis-open.org/odata/ns/edm">

{"".join(entity_types)}

      <!-- Entity Container -->
      <EntityContainer Name="Container">
{chr(10).join(entity_sets)}
      </EntityContainer>

{annotations}
    </Schema>
  </edmx:DataServices>
</edmx:Edmx>'''

        return HttpResponse(metadata_xml, content_type="application/xml; charset=utf-8")

    def _generate_entity_type(
        self,
        name: str,
        model_class: type[models.Model],
        dto_class: type | None,
        namespace: str,
        registered_models: set[type[models.Model]],
        expandable_fields: dict[str, type],
    ) -> str:
        """Generate XML for an entity type.

        Only includes navigation properties for fields configured in
        the selector's expandable_fields to ensure metadata matches API capabilities.
        """
        lines = [f"      <!-- {name} Entity Type -->"]
        lines.append(f'      <EntityType Name="{name}">')
        lines.append("        <Key>")
        lines.append('          <PropertyRef Name="id"/>')
        lines.append("        </Key>")

        # Get fields from model
        for field in model_class._meta.get_fields():
            if isinstance(field, (models.ManyToOneRel, models.ManyToManyRel)):
                # Reverse relations - only add if in expandable_fields
                related_name = field.get_accessor_name()
                if related_name not in expandable_fields:
                    continue
                if field.related_model not in registered_models:
                    continue
                related_model = field.related_model.__name__
                lines.append(
                    f'        <NavigationProperty Name="{related_name}" '
                    f'Type="Collection({namespace}.{related_model})"/>'
                )
            elif isinstance(field, models.ForeignKey):
                # FK - only add if in expandable_fields
                if field.name not in expandable_fields:
                    continue
                if field.related_model not in registered_models:
                    continue
                edm_type = f"{namespace}.{field.related_model.__name__}"
                nullable = "true" if field.null else "false"
                lines.append(
                    f'        <NavigationProperty Name="{field.name}" Type="{edm_type}" Nullable="{nullable}"/>'
                )
            elif isinstance(field, models.ManyToManyField):
                # M2M - only add if in expandable_fields
                if field.name not in expandable_fields:
                    continue
                if field.related_model not in registered_models:
                    continue
                related_model = field.related_model.__name__
                lines.append(
                    f'        <NavigationProperty Name="{field.name}" Type="Collection({namespace}.{related_model})"/>'
                )
            elif hasattr(field, "get_internal_type"):
                # Regular field
                edm_type = self._django_to_edm_type(field)
                nullable = "true" if getattr(field, "null", True) else "false"

                # Skip auto fields and password
                if field.name == "password":
                    continue

                lines.append(f'        <Property Name="{field.name}" Type="{edm_type}" Nullable="{nullable}"/>')

        lines.append("      </EntityType>")
        lines.append("")

        return "\n".join(lines)

    def _django_to_edm_type(self, field: models.Field) -> str:
        """Convert Django field type to EDM type."""
        type_map = {
            "AutoField": "Edm.Int32",
            "BigAutoField": "Edm.Int64",
            "IntegerField": "Edm.Int32",
            "BigIntegerField": "Edm.Int64",
            "SmallIntegerField": "Edm.Int16",
            "PositiveIntegerField": "Edm.Int32",
            "PositiveSmallIntegerField": "Edm.Int16",
            "FloatField": "Edm.Double",
            "DecimalField": "Edm.Decimal",
            "CharField": "Edm.String",
            "TextField": "Edm.String",
            "SlugField": "Edm.String",
            "EmailField": "Edm.String",
            "URLField": "Edm.String",
            "BooleanField": "Edm.Boolean",
            "NullBooleanField": "Edm.Boolean",
            "DateField": "Edm.Date",
            "DateTimeField": "Edm.DateTimeOffset",
            "TimeField": "Edm.TimeOfDay",
            "DurationField": "Edm.Duration",
            "UUIDField": "Edm.Guid",
            "BinaryField": "Edm.Binary",
            "FileField": "Edm.String",
            "ImageField": "Edm.String",
        }
        internal_type = field.get_internal_type()
        return type_map.get(internal_type, "Edm.String")

    def _get_navigation_bindings(
        self,
        model_class: type[models.Model],
        selectors: dict[str, type[ODataSelector]],
        expandable_fields: dict[str, type],
    ) -> dict[str, str]:
        """Get navigation property bindings for an entity set.

        Only includes bindings for fields in expandable_fields.
        """
        bindings = {}

        # Build reverse lookup: model -> entity_set_name
        model_to_entity_set = {}
        for entity_set_name, selector_class in selectors.items():
            selector = selector_class()
            if selector.model:
                model_to_entity_set[selector.model] = entity_set_name

        for field in model_class._meta.get_fields():
            if isinstance(field, models.ForeignKey):
                if field.name not in expandable_fields:
                    continue
                target_model = field.related_model
                if target_model in model_to_entity_set:
                    bindings[field.name] = model_to_entity_set[target_model]
            elif isinstance(field, models.ManyToManyField):
                if field.name not in expandable_fields:
                    continue
                target_model = field.related_model
                if target_model in model_to_entity_set:
                    bindings[field.name] = model_to_entity_set[target_model]
            elif isinstance(field, (models.ManyToOneRel, models.ManyToManyRel)):
                accessor_name = field.get_accessor_name()
                if accessor_name not in expandable_fields:
                    continue
                target_model = field.related_model
                if target_model in model_to_entity_set:
                    bindings[accessor_name] = model_to_entity_set[target_model]

        return bindings

    def _generate_capabilities_annotations(
        self,
        selectors: dict[str, type[ODataSelector]],
        namespace: str,
    ) -> str:
        """Generate OData Capabilities vocabulary annotations.

        Generates FilterRestrictions and SortRestrictions annotations
        for each entity set based on selector configuration.

        See: https://github.com/oasis-tcs/odata-vocabularies/blob/main/vocabularies/Org.OData.Capabilities.V1.md
        """
        lines = ["      <!-- Capabilities Annotations -->"]
        lines.append('      <Annotations xmlns="http://docs.oasis-open.org/odata/ns/edm">')

        for entity_set_name, selector_class in selectors.items():
            selector = selector_class()
            target = f"{namespace}.Container/{entity_set_name}"

            lines.append(f'        <Annotation Target="{target}" Term="Org.OData.Capabilities.V1.FilterRestrictions">')
            lines.append("          <Record>")
            lines.append(
                f'            <PropertyValue Property="Filterable" Bool="{str(selector.is_filterable()).lower()}"/>'
            )

            non_filterable = selector.get_non_filterable_fields()
            if non_filterable:
                lines.append('            <PropertyValue Property="NonFilterableProperties">')
                lines.append("              <Collection>")
                for field in non_filterable:
                    lines.append(f"                <PropertyPath>{field}</PropertyPath>")
                lines.append("              </Collection>")
                lines.append("            </PropertyValue>")

            lines.append("          </Record>")
            lines.append("        </Annotation>")

            lines.append(f'        <Annotation Target="{target}" Term="Org.OData.Capabilities.V1.SortRestrictions">')
            lines.append("          <Record>")
            lines.append(
                f'            <PropertyValue Property="Sortable" Bool="{str(selector.is_sortable()).lower()}"/>'
            )

            non_sortable = selector.get_non_sortable_fields()
            if non_sortable:
                lines.append('            <PropertyValue Property="NonSortableProperties">')
                lines.append("              <Collection>")
                for field in non_sortable:
                    lines.append(f"                <PropertyPath>{field}</PropertyPath>")
                lines.append("              </Collection>")
                lines.append("            </PropertyValue>")

            lines.append("          </Record>")
            lines.append("        </Annotation>")

        lines.append("      </Annotations>")

        return "\n".join(lines)


class ODataServiceDocumentView(View):
    """
    OData service document endpoint.

    Returns a JSON document listing all available entity sets.

    Usage in urls.py:
        path("odata/", ODataServiceDocumentView.as_view(), name="odata-service"),
    """

    def get(self, request, *args, **kwargs):
        """Return OData service document."""
        base_url = request.build_absolute_uri("/odata/")
        selectors = ODataMetadataRegistry.get_selectors()

        entity_sets = [
            {"name": entity_set_name, "kind": "EntitySet", "url": entity_set_name}
            for entity_set_name in selectors.keys()
        ]

        service_doc = {"@odata.context": f"{base_url}$metadata", "value": entity_sets}

        return JsonResponse(service_doc)

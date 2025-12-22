"""
OData serializers for Django REST Framework.

Provides OData-enabled serializers with field selection and expansion support.
"""

from rest_framework import serializers

from fc_selector.django.drf.mixins import ODataSerializerMixin


class ODataSerializer(ODataSerializerMixin, serializers.Serializer):
    """
    Base OData serializer for non-model serializers.

    Provides OData-specific serialization logic including field selection
    and nested object handling.

    Example:
        class AuthorSerializer(ODataSerializer):
            id = serializers.IntegerField()
            name = serializers.CharField()
            email = serializers.EmailField()
    """

    pass


class ODataModelSerializer(ODataSerializerMixin, serializers.ModelSerializer):
    """
    OData-enabled ModelSerializer for Django models.

    Provides OData-specific serialization logic including field selection,
    nested object handling, and automatic field generation from model.

    Example:
        class BlogPostSerializer(ODataModelSerializer):
            class Meta:
                model = BlogPost
                fields = ['id', 'title', 'content', 'author', 'created_at']
                
            # Now supports OData queries:
            # $select=id,title - Only include selected fields
            # $expand=author - Include related author object
    """

    pass

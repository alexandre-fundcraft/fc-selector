"""
Base OData viewset for non-model viewsets.

Provides OData query support for generic viewsets.
"""

from rest_framework import viewsets

from fc_selector.django.drf.mixins import ODataMixin


class ODataViewSet(ODataMixin, viewsets.ViewSet):
    """
    Base OData ViewSet that provides OData query support for non-model viewsets.

    This viewset provides:
    - OData query parameter parsing and application
    - OData-formatted responses
    - $metadata endpoint support
    - Service document endpoint support

    Example:
        class CustomViewSet(ODataViewSet):
            def list(self, request):
                # OData parameters are automatically applied
                queryset = self.apply_odata_query(MyModel.objects.all())
                serializer = MySerializer(queryset, many=True)
                return Response(serializer.data)
    """

    pass

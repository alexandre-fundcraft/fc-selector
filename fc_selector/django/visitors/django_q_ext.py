"""
Custom Django Lookups for OData.

This module provides custom Django lookups used by the FilterVisitor.

Original Code: https://github.com/gorilla-co/odata-query
License: MIT
Authors: Original odata-query authors
Modified by: Alexandre Busquets (django-odata)
"""

from django.db.models import Lookup, fields


@fields.Field.register_lookup
class NotEqual(Lookup):
    """Custom NotEqual lookup for OData ne operator.

    https://docs.djangoproject.com/en/2.2/howto/custom-lookups/
    """

    lookup_name = "ne"

    def as_sql(self, compiler, connection):  # type: ignore
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        params = lhs_params + rhs_params
        return f"{lhs} <> {rhs}", params

"""
Test models for django-odata test suite.
"""

from django.db import models


class ODataTestModel(models.Model):
    """Test model with various field types for comprehensive OData testing."""

    # String fields
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    # Numeric fields
    count = models.IntegerField(default=0)
    rating = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)

    # Boolean field
    is_active = models.BooleanField(default=True)

    # Date/Time fields
    created_at = models.DateTimeField()
    published_date = models.DateField(null=True, blank=True)

    # Choice field
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("published", "Published"),
        ("archived", "Archived"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")

    class Meta:
        pass


class ODataRelatedModel(models.Model):
    """Related model for testing navigation properties."""

    test_model = models.ForeignKey(ODataTestModel, on_delete=models.CASCADE, related_name="related_items")
    title = models.CharField(max_length=50)
    value = models.IntegerField()

    class Meta:
        pass


class PerformanceTestModel(models.Model):
    """Model for performance testing with various indexed fields."""

    name = models.CharField(max_length=100, db_index=True)
    category = models.CharField(max_length=50, db_index=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, db_index=True)
    quantity = models.IntegerField(db_index=True)
    is_available = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["category", "is_available"]),
            models.Index(fields=["price", "quantity"]),
            models.Index(fields=["created_at", "rating"]),
        ]


class PerformanceRelatedModel(models.Model):
    """Related model for testing join performance."""

    parent = models.ForeignKey(PerformanceTestModel, on_delete=models.CASCADE, related_name="related_items")
    tag = models.CharField(max_length=30)
    weight = models.IntegerField()

    class Meta:
        pass


class ODataFKTarget(models.Model):
    """Target model for FK testing in hybrid values mode."""

    name = models.CharField(max_length=100)
    code = models.CharField(max_length=10)

    class Meta:
        pass


class ODataModelWithFK(models.Model):
    """Model with forward FK for hybrid values testing."""

    title = models.CharField(max_length=100)
    value = models.IntegerField(default=0)
    target = models.ForeignKey(ODataFKTarget, on_delete=models.CASCADE, null=True, blank=True)
    second_target = models.ForeignKey(
        ODataFKTarget,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reverse_second",
    )

    class Meta:
        pass


class ODataM2MTarget(models.Model):
    """Target model for M2M testing in hybrid values mode."""

    name = models.CharField(max_length=100)

    class Meta:
        pass


class ODataModelWithRelations(models.Model):
    """Model with forward FK, reverse FK, and M2M for hybrid values testing."""

    title = models.CharField(max_length=100)
    value = models.IntegerField(default=0)
    target = models.ForeignKey(
        ODataFKTarget, on_delete=models.CASCADE, null=True, blank=True, related_name="parent_items"
    )
    tags = models.ManyToManyField(ODataM2MTarget, related_name="tagged_items", blank=True)

    class Meta:
        pass


class ODataChildModel(models.Model):
    """Child model for reverse FK testing in hybrid values mode."""

    parent = models.ForeignKey(
        ODataModelWithRelations, on_delete=models.CASCADE, related_name="children"
    )
    label = models.CharField(max_length=100)
    score = models.IntegerField(default=0)
    category = models.ForeignKey(ODataM2MTarget, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        pass


class ODataGrandChildModel(models.Model):
    """Grandchild model for recursive nested reverse FK expand testing."""

    child = models.ForeignKey(
        ODataChildModel, on_delete=models.CASCADE, related_name="grandchildren"
    )
    note = models.CharField(max_length=100)

    class Meta:
        pass


class ODataOneToOneChild(models.Model):
    """Child model for OneToOne testing."""

    name = models.CharField(max_length=50)

    class Meta:
        pass


class ODataOneToOneParent(models.Model):
    """Parent model with OneToOne and property for testing executor optimization."""

    child = models.OneToOneField(ODataOneToOneChild, on_delete=models.CASCADE)
    description = models.CharField(max_length=50)

    @property
    def full_desc(self):
        """Property accessing related field."""
        return f"{self.child.name}: {self.description}"

    class Meta:
        pass


class ODataRootModel(models.Model):
    """Root model pointing to a parent with OneToOne."""

    parent = models.ForeignKey(ODataOneToOneParent, on_delete=models.CASCADE, related_name="roots")

    class Meta:
        pass


class ODataSimpleParent(models.Model):
    """Parent model with OneToOne but NO properties."""
    child = models.OneToOneField(ODataOneToOneChild, on_delete=models.CASCADE)
    description = models.CharField(max_length=50)

    class Meta:
        pass


class ODataSimpleRoot(models.Model):
    """Root model pointing to simple parent."""
    parent = models.ForeignKey(ODataSimpleParent, on_delete=models.CASCADE)

    class Meta:
        pass


class ODataSelfM2MModel(models.Model):
    """Model with self-referential M2M for testing."""
    name = models.CharField(max_length=100)
    friends = models.ManyToManyField("self", symmetrical=False, related_name="friend_of")

    class Meta:
        pass

"""
Example DTO serializers for blog app.

This shows how to use ODataDTOSerializer with customization like hiding passwords.
"""

from fc_selector.django.drf.serializers import ODataDTOSerializer

from .selectors.blog_post import (
    AuthorDTO,
    BlogPostDTO,
    CategoryDTO,
    CommentDTO,
    TagDTO,
    UserDTO,
)


class UserDTOSerializer(ODataDTOSerializer):
    """
    Serializer for UserDTO with password excluded.

    Demonstrates field exclusion - password is never included in API responses.
    """

    class Meta:
        dto_class = UserDTO
        exclude = ["password"]  # Hide password field
        read_only_fields = ["id", "last_login", "date_joined"]


class AuthorDTOSerializer(ODataDTOSerializer):
    """Serializer for AuthorDTO."""

    class Meta:
        dto_class = AuthorDTO
        read_only_fields = ["id", "created_at"]


class CategoryDTOSerializer(ODataDTOSerializer):
    """Serializer for CategoryDTO."""

    class Meta:
        dto_class = CategoryDTO
        read_only_fields = ["id", "created_at"]


class BlogPostDTOSerializer(ODataDTOSerializer):
    """
    Serializer for BlogPostDTO with customizations.

    Demonstrates:
    - Read-only fields (id, timestamps)
    - Nested DTOs (author, categories) are automatically handled
    """

    class Meta:
        dto_class = BlogPostDTO
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "published_at",
            "view_count",
        ]
        # You can also explicitly define which fields to include
        # fields = ['id', 'title', 'content', 'author', 'categories']


class CommentDTOSerializer(ODataDTOSerializer):
    """Serializer for CommentDTO.

    The 'post' expand uses BlogPostSummaryDTO (DB fields only),
    which enables hybrid values mode for faster queries.
    """

    class Meta:
        dto_class = CommentDTO
        read_only_fields = ["id", "created_at"]


class TagDTOSerializer(ODataDTOSerializer):
    """Serializer for TagDTO."""

    class Meta:
        dto_class = TagDTO
        read_only_fields = ["id"]

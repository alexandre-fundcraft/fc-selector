"""
Pytest configuration for django-odata tests.
"""

import os

import pytest

# Ensure pytest-django can find the test Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")

from example.blog.models import Author, BlogPost, Category


@pytest.fixture
def blog_post_model():
    """Fixture providing the BlogPost model."""
    return BlogPost


@pytest.fixture
def author_model():
    """Fixture providing the Author model."""
    return Author


@pytest.fixture
def category_model():
    """Fixture providing the Category model."""
    return Category

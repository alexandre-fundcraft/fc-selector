"""
E2E Test Fixtures.

Sets up a realistic database scenario with Authors, Posts, Categories and Comments
to test OData queries thoroughly.
"""

import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient

from example.blog.models import Author, BlogPost, Category


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def scenario_data(db):
    """
    Creates a rich data scenario:
    - 3 Users/Authors (Alice, Bob, Charlie)
    - 2 Categories (Tech, Life)
    - 15 Posts mixed
    """
    # 1. Categories
    cat_tech = Category.objects.create(name="Technology", description="Tech stuff")
    cat_life = Category.objects.create(name="Lifestyle", description="Life stuff")

    # 2. Authors
    u_alice = User.objects.create_user("alice", "alice@example.com", "pass")
    author_alice = Author.objects.create(user=u_alice, bio="I am Alice")

    u_bob = User.objects.create_user("bob", "bob@example.com", "pass")
    author_bob = Author.objects.create(user=u_bob, bio="I am Bob")

    u_charlie = User.objects.create_user("charlie", "charlie@example.com", "pass")
    author_charlie = Author.objects.create(user=u_charlie, bio="I am Charlie")

    # 3. Posts
    posts = []

    # Alice's Posts (5 Tech, Published)
    for i in range(1, 6):
        p = BlogPost.objects.create(
            title=f"Alice Tech Post {i}",
            slug=f"alice-tech-{i}",
            content=f"Content about tech {i}",
            author=author_alice,
            status="published",
            view_count=100 * i,
            rating=4.5,
        )
        p.categories.add(cat_tech)
        posts.append(p)

    # Bob's Posts (5 Life, Draft)
    for i in range(1, 6):
        p = BlogPost.objects.create(
            title=f"Bob Life Post {i}",
            slug=f"bob-life-{i}",
            content=f"Content about life {i}",
            author=author_bob,
            status="draft",
            view_count=10 * i,
            rating=3.0,
        )
        p.categories.add(cat_life)
        posts.append(p)

    # Charlie's Posts (5 Mixed, Featured)
    for i in range(1, 6):
        p = BlogPost.objects.create(
            title=f"Charlie Mixed Post {i}",
            slug=f"charlie-mixed-{i}",
            content=f"Content about mixed {i}",
            author=author_charlie,
            status="published",
            featured=True,
            view_count=500 * i,
            rating=5.0,
        )
        p.categories.add(cat_tech, cat_life)
        posts.append(p)

    return {"authors": [author_alice, author_bob, author_charlie], "categories": [cat_tech, cat_life], "posts": posts}

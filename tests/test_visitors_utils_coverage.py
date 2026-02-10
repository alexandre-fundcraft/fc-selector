import pytest

from example.blog.models import BlogPost
from fc_selector.core import exceptions as core_ex
from fc_selector.django.visitors import utils as vutils


def test_reverse_relationship_empty_expr_raises():
    with pytest.raises(core_ex.InvalidFieldError):
        vutils.reverse_relationship("", BlogPost)


def test_reverse_relationship_empty_segment_raises():
    with pytest.raises(core_ex.InvalidFieldError):
        vutils.reverse_relationship("author__", BlogPost)


def test_reverse_relationship_nonexistent_field_raises():
    with pytest.raises(core_ex.FieldNotFoundError):
        vutils.reverse_relationship("nope", BlogPost)


def test_reverse_relationship_non_relation_raises():
    # title is a CharField, not a relation
    with pytest.raises(core_ex.InvalidFieldError):
        vutils.reverse_relationship("title", BlogPost)


def test_reverse_relationship_happy_path():
    # BlogPost.author -> reverse remote field name should be 'blogpost_set' on Author
    path, model = vutils.reverse_relationship("author", BlogPost)
    assert path in {"blogpost_set", "posts"}
    assert model.__name__ in {"Author", "User"}

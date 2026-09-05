"""
Tests for AST rewriting utilities.

Covers fc_selector/protocols/odata/parsers/filter/rewrite.py
"""

from fc_selector.core import ast
from fc_selector.protocols.odata.parsers.filter.rewrite import (
    IdentifierStripper,
)


class TestIdentifierStripper:
    """Tests for IdentifierStripper transformer."""

    def test_strip_identifier_from_attribute(self):
        """Identifier is stripped from attribute."""
        strip_id = ast.Identifier("x")
        stripper = IdentifierStripper(strip_id)

        # x/name should become just name
        attr_node = ast.Attribute(owner=ast.Identifier("x"), attr="name")
        result = stripper.visit(attr_node)

        assert isinstance(result, ast.Identifier)
        assert result.name == "name"

    def test_non_matching_identifier_unchanged(self):
        """Non-matching identifier is unchanged."""
        strip_id = ast.Identifier("x")
        stripper = IdentifierStripper(strip_id)

        # y/name should stay y/name
        attr_node = ast.Attribute(owner=ast.Identifier("y"), attr="name")
        result = stripper.visit(attr_node)

        assert isinstance(result, ast.Attribute)
        assert result.attr == "name"

    def test_nested_attribute_stripped(self):
        """Nested attribute is stripped correctly."""
        strip_id = ast.Identifier("x")
        stripper = IdentifierStripper(strip_id)

        # x/author/name should become author/name
        inner_attr = ast.Attribute(owner=ast.Identifier("x"), attr="author")
        outer_attr = ast.Attribute(owner=inner_attr, attr="name")
        result = stripper.visit(outer_attr)

        # After stripping x, we should have author/name
        assert isinstance(result, ast.Attribute)
        assert result.attr == "name"

    def test_deeply_nested_non_matching(self):
        """Deeply nested non-matching attribute."""
        strip_id = ast.Identifier("x")
        stripper = IdentifierStripper(strip_id)

        # y/author/name - y doesn't match x
        inner_attr = ast.Attribute(owner=ast.Identifier("y"), attr="author")
        outer_attr = ast.Attribute(owner=inner_attr, attr="name")
        result = stripper.visit(outer_attr)

        # Should be unchanged
        assert isinstance(result, ast.Attribute)

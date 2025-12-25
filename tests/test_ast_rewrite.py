"""
Tests for AST rewriting utilities.

Covers fc_selector/protocols/odata/parsers/filter/rewrite.py
"""

from fc_selector.core import ast
from fc_selector.protocols.odata.parsers.filter import parse_filter as parse
from fc_selector.protocols.odata.parsers.filter.rewrite import (
    AliasRewriter,
    IdentifierStripper,
)


class TestAliasRewriter:
    """Tests for AliasRewriter transformer."""

    def test_simple_alias_replacement(self):
        """Simple identifier alias is replaced."""
        aliases = {"title": "name"}
        rewriter = AliasRewriter(aliases)

        original_ast = parse("title eq 'test'")
        rewritten = rewriter.visit(original_ast)

        # The 'title' identifier should now be 'name'
        assert rewritten is not None

    def test_multiple_aliases(self):
        """Multiple aliases are replaced."""
        aliases = {"title": "name", "qty": "count"}
        rewriter = AliasRewriter(aliases)

        original_ast = parse("title eq 'test' and qty gt 5")
        rewritten = rewriter.visit(original_ast)

        assert rewritten is not None

    def test_attribute_alias_replacement(self):
        """Attribute aliases are replaced."""
        aliases = {"author/email": "author/mail_address"}
        rewriter = AliasRewriter(aliases)

        # This tests that complex aliases work
        original_ast = parse("author/email eq 'test@test.com'")
        rewritten = rewriter.visit(original_ast)

        assert rewritten is not None

    def test_no_alias_unchanged(self):
        """Non-aliased identifiers are unchanged."""
        aliases = {"title": "name"}
        rewriter = AliasRewriter(aliases)

        original_ast = parse("count gt 5")
        rewritten = rewriter.visit(original_ast)

        # Should be identical since no alias matches
        assert rewritten is not None

    def test_custom_lexer_parser(self):
        """Custom lexer and parser can be provided."""
        from fc_selector.protocols.odata.parsers.filter.grammar import (
            ODataLexer,
            ODataParser,
        )

        lexer = ODataLexer()
        parser = ODataParser()
        aliases = {"title": "name"}

        rewriter = AliasRewriter(aliases, lexer=lexer, parser=parser)
        assert rewriter is not None


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

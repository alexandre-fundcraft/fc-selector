"""
OData Filter Expression Parser.

This package provides:
- AST nodes for OData filter expressions
- Lexer and parser for OData $filter expressions using SLY
- Visitor pattern for traversing and transforming AST
- Type checking and rewriting utilities

Original Code: https://github.com/gorilla-co/odata-query
License: MIT
Authors: Original odata-query authors
Modified by: Alexandre Busquets (django-odata)

Usage:
    from django_odata.core.parsers.filter import ODataLexer, ODataParser, ast

    lexer = ODataLexer()
    parser = ODataParser()

    query = "name eq 'John' and age gt 30"
    tokens = lexer.tokenize(query)
    ast_tree = parser.parse(tokens)

    # ast_tree is now a tree of AST nodes
"""

from . import ast, rewrite, typing, utils
from .exceptions import (
    ODataException,
    ODataSyntaxError,
    ParsingException,
    TokenizingException,
    TypeException,
    UnsupportedFunctionException,
    ValueException,
)
from .grammar import ODataLexer, ODataParser


def parse_filter(filter_expression: str):
    """
    Parse an OData filter expression into an AST.

    Args:
        filter_expression: OData filter string (e.g., "name eq 'John'")

    Returns:
        AST root node

    Example:
        >>> ast_tree = parse_filter("name eq 'John' and age gt 30")
    """
    lexer = ODataLexer()
    parser = ODataParser()
    tokens = lexer.tokenize(filter_expression)
    return parser.parse(tokens)


__all__ = [
    # AST & utilities
    "ast",
    "typing",
    "utils",
    "rewrite",
    # Parser
    "ODataLexer",
    "ODataParser",
    "parse_filter",
    # Exceptions
    "ODataException",
    "ODataSyntaxError",
    "TokenizingException",
    "ParsingException",
    "UnsupportedFunctionException",
    "TypeException",
    "ValueException",
]

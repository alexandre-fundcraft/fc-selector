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
    from fc_selector.protocols.odata.parsers.filter import ODataLexer, ODataParser
    from fc_selector.core import ast

    lexer = ODataLexer()
    parser = ODataParser()

    query = "name eq 'John' and age gt 30"
    tokens = lexer.tokenize(query)
    ast_tree = parser.parse(tokens)

    # ast_tree is now a tree of AST nodes
"""

import threading

from fc_selector.core import ast

from . import rewrite, typing, utils
from .exceptions import (
    ODataException,
    ODataSyntaxError,
    ParsingException,
    TokenizingException,
)
from .grammar import ODataLexer, ODataParser

# Thread-local storage for parser instances (thread-safe caching)
_thread_local = threading.local()

# Configuration
MAX_FILTER_LENGTH = 4000  # Maximum filter expression length


def _get_lexer() -> ODataLexer:
    """Get thread-local lexer instance."""
    if not hasattr(_thread_local, "lexer"):
        _thread_local.lexer = ODataLexer()
    lexer: ODataLexer = _thread_local.lexer
    return lexer


def _get_parser() -> ODataParser:
    """Get thread-local parser instance."""
    if not hasattr(_thread_local, "parser"):
        _thread_local.parser = ODataParser()
    parser: ODataParser = _thread_local.parser
    return parser


def parse_filter(filter_expression: str) -> ast.Node:
    """
    Parse an OData filter expression into an AST.

    Args:
        filter_expression: OData filter string (e.g., "name eq 'John'")

    Returns:
        AST root node

    Raises:
        ODataSyntaxError: If filter expression exceeds MAX_FILTER_LENGTH or has syntax errors

    Example:
        >>> ast_tree = parse_filter("name eq 'John' and age gt 30")
    """
    # Input length validation to prevent DoS attacks
    if len(filter_expression) > MAX_FILTER_LENGTH:
        raise ODataSyntaxError(f"Filter expression too long: {len(filter_expression)} chars (max {MAX_FILTER_LENGTH})")

    lexer = _get_lexer()
    parser = _get_parser()
    tokens = lexer.tokenize(filter_expression)
    result: ast.Node = parser.parse(tokens)
    return result


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
]

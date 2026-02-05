#!/usr/bin/env python3
"""
Find methods that could be @staticmethod by analyzing AST.
"""

import ast
import sys
from pathlib import Path


class StaticMethodFinder(ast.NodeVisitor):
    """Find methods that don't use self or cls."""

    def __init__(self, filepath):
        self.filepath = filepath
        self.candidates = []
        self.current_class = None

    def visit_ClassDef(self, node):
        """Visit class definition."""
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class

    def visit_FunctionDef(self, node):
        """Visit function definition."""
        # Skip if not in a class
        if not self.current_class:
            return

        # Skip if already has @staticmethod or @classmethod
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name):
                if decorator.id in ("staticmethod", "classmethod"):
                    return
            elif isinstance(decorator, ast.Attribute):
                if decorator.attr in ("staticmethod", "classmethod"):
                    return

        # Skip special methods (except __new__)
        if node.name.startswith("__") and node.name.endswith("__"):
            if node.name != "__new__":
                return

        # Skip if no arguments
        if not node.args.args:
            return

        first_arg = node.args.args[0].arg

        # Skip if first arg is not self or cls
        if first_arg not in ("self", "cls"):
            return

        # Check if self/cls is used in the method body
        uses_first_arg = self._uses_name(node, first_arg)

        if not uses_first_arg:
            self.candidates.append(
                {
                    "class": self.current_class,
                    "method": node.name,
                    "line": node.lineno,
                    "first_arg": first_arg,
                }
            )

    def _uses_name(self, node, name):
        """Check if a name is used in the node."""
        for child in ast.walk(node):
            if isinstance(child, ast.Name) and child.id == name:
                # Make sure it's not the parameter definition itself
                if child.lineno != node.lineno:
                    return True
            elif isinstance(child, ast.arg) and child.arg == name:
                # Skip the parameter definition
                continue
        return False


def find_candidates_in_file(filepath):
    """Find @staticmethod candidates in a file."""
    try:
        with open(filepath, "r") as f:
            source = f.read()

        tree = ast.parse(source, filename=str(filepath))
        finder = StaticMethodFinder(filepath)
        finder.visit(tree)
        return finder.candidates
    except SyntaxError as e:
        print(f"Syntax error in {filepath}: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"Error processing {filepath}: {e}", file=sys.stderr)
        return []


def main():
    """Main function."""
    root = Path("fc_selector")

    all_candidates = []

    for py_file in sorted(root.rglob("*.py")):
        candidates = find_candidates_in_file(py_file)
        if candidates:
            all_candidates.extend([(py_file, c) for c in candidates])

    if not all_candidates:
        print("No @staticmethod candidates found!")
        return 0

    print(f"Found {len(all_candidates)} @staticmethod candidates:\n")

    # Group by file
    by_file = {}
    for filepath, candidate in all_candidates:
        if filepath not in by_file:
            by_file[filepath] = []
        by_file[filepath].append(candidate)

    for filepath in sorted(by_file.keys()):
        print(f"\n{filepath}:")
        for candidate in sorted(by_file[filepath], key=lambda x: x["line"]):
            print(f"  Line {candidate['line']:4d}: {candidate['class']}.{candidate['method']}")

    print(f"\n\nTotal: {len(all_candidates)} candidates")
    return 0


if __name__ == "__main__":
    sys.exit(main())

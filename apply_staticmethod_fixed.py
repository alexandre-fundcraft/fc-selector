#!/usr/bin/env python3
"""
Apply @staticmethod decorators to methods that don't use self/cls.
Fixed version that places decorators correctly.
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

        if not node.args.args:
            return

        first_arg = node.args.args[0].arg

        if first_arg not in ("self", "cls"):
            return

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
                if child.lineno != node.lineno:
                    return True
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
    except Exception as e:
        print(f"Error processing {filepath}: {e}", file=sys.stderr)
        return []


def add_staticmethod_to_file(filepath, candidates):
    """Add @staticmethod decorators to a file."""
    with open(filepath, "r") as f:
        lines = f.readlines()

    # Sort by line number descending to avoid line shifts
    candidates = sorted(candidates, key=lambda x: x["line"], reverse=True)

    modified = 0
    for candidate in candidates:
        line_idx = candidate["line"] - 1  # Convert to 0-indexed

        # Find where to insert @staticmethod
        # Look backward for existing decorators or docstrings
        insert_idx = line_idx

        # Check if there are existing decorators above
        temp_idx = line_idx - 1
        while temp_idx >= 0:
            stripped = lines[temp_idx].strip()
            if stripped.startswith("@"):
                # Found existing decorator, insert before it
                insert_idx = temp_idx
                temp_idx -= 1
            elif stripped == "" or stripped.startswith('"""') or stripped.startswith("'''"):
                # Skip empty lines and docstrings
                temp_idx -= 1
            else:
                # Found code, stop
                break

        # Get indentation from the def line
        def_line = lines[line_idx]
        indent = len(def_line) - len(def_line.lstrip())
        indent_str = " " * indent

        # Insert @staticmethod at the correct position
        lines.insert(insert_idx, f"{indent_str}@staticmethod\n")
        modified += 1

    # Write back
    with open(filepath, "w") as f:
        f.writelines(lines)

    return modified


def main():
    """Main function."""
    root = Path("fc_selector")

    all_candidates = []
    by_file = {}

    for py_file in sorted(root.rglob("*.py")):
        candidates = find_candidates_in_file(py_file)
        if candidates:
            by_file[py_file] = candidates
            all_candidates.extend(candidates)

    if not all_candidates:
        print("No @staticmethod candidates found!")
        return 0

    print(f"Found {len(all_candidates)} candidates in {len(by_file)} files\n")

    total_modified = 0
    for filepath, candidates in sorted(by_file.items()):
        print(f"Processing {filepath} ({len(candidates)} methods)...")
        modified = add_staticmethod_to_file(filepath, candidates)
        total_modified += modified

    print(f"\n✅ Added @staticmethod to {total_modified} methods")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Apply @staticmethod decorators to methods that don't use self/cls.
Smart detection that catches all forms of self usage.
"""

import ast
import sys
from pathlib import Path


class SelfUsageChecker(ast.NodeVisitor):
    """Check if self/cls is used in a function."""

    def __init__(self, param_name):
        self.param_name = param_name
        self.uses_param = False
        self.in_nested_function = False

    def visit_FunctionDef(self, node):
        """Don't recurse into nested functions."""
        # Nested functions have their own scope
        old_nested = self.in_nested_function
        self.in_nested_function = True
        self.generic_visit(node)
        self.in_nested_function = old_nested

    def visit_Lambda(self, node):
        """Don't recurse into lambdas."""
        old_nested = self.in_nested_function
        self.in_nested_function = True
        self.generic_visit(node)
        self.in_nested_function = old_nested

    def visit_Name(self, node):
        """Check for direct name usage (self, cls)."""
        if not self.in_nested_function and node.id == self.param_name:
            self.uses_param = True

    def visit_Attribute(self, node):
        """Check for attribute access (self.attr, self.method)."""
        # Check if owner is self/cls
        if isinstance(node.value, ast.Name) and node.value.id == self.param_name:
            if not self.in_nested_function:
                self.uses_param = True
        # Recursively check the value
        self.visit(node.value)

    def visit_Call(self, node):
        """Check for super() calls."""
        if isinstance(node.func, ast.Name) and node.func.id == "super":
            if not self.in_nested_function:
                self.uses_param = True
        self.generic_visit(node)


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
                if decorator.id in ("staticmethod", "classmethod", "property"):
                    return
            elif isinstance(decorator, ast.Attribute):
                if decorator.attr in ("staticmethod", "classmethod", "property"):
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

        # Check if self/cls is actually used
        checker = SelfUsageChecker(first_arg)

        # Don't check the function signature itself
        for stmt in node.body:
            checker.visit(stmt)

        if not checker.uses_param:
            self.candidates.append(
                {
                    "class": self.current_class,
                    "method": node.name,
                    "line": node.lineno,
                    "first_arg": first_arg,
                }
            )


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
        line_idx = candidate["line"] - 1

        # Find where to insert @staticmethod
        insert_idx = line_idx

        # Check for existing decorators
        temp_idx = line_idx - 1
        while temp_idx >= 0:
            stripped = lines[temp_idx].strip()
            if stripped.startswith("@"):
                insert_idx = temp_idx
                temp_idx -= 1
            elif stripped == "" or stripped.startswith('"""') or stripped.startswith("'''"):
                temp_idx -= 1
            else:
                break

        # Get indentation
        def_line = lines[line_idx]
        indent = len(def_line) - len(def_line.lstrip())
        indent_str = " " * indent

        # Insert @staticmethod
        lines.insert(insert_idx, f"{indent_str}@staticmethod\n")
        modified += 1

    with open(filepath, "w") as f:
        f.writelines(lines)

    return modified


def main():
    """Main function."""
    root = Path("fc_selector")

    # Files to exclude (SLY parser/lexer can't use @staticmethod)
    exclude_files = {
        "fc_selector/protocols/odata/parsers/filter/grammar.py",
    }

    all_candidates = []
    by_file = {}

    for py_file in sorted(root.rglob("*.py")):
        if str(py_file) in exclude_files:
            print(f"Skipping {py_file} (SLY parser/lexer)")
            continue

        candidates = find_candidates_in_file(py_file)
        if candidates:
            by_file[py_file] = candidates
            all_candidates.extend(candidates)

    if not all_candidates:
        print("No @staticmethod candidates found!")
        return 0

    print(f"\nFound {len(all_candidates)} candidates in {len(by_file)} files\n")

    total_modified = 0
    for filepath, candidates in sorted(by_file.items()):
        print(f"Processing {filepath} ({len(candidates)} methods)...")
        modified = add_staticmethod_to_file(filepath, candidates)
        total_modified += modified

    print(f"\n✅ Added @staticmethod to {total_modified} methods")
    return 0


if __name__ == "__main__":
    sys.exit(main())

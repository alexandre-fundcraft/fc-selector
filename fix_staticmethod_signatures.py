#!/usr/bin/env python3
"""
Remove 'self' parameter from @staticmethod decorated methods.
"""

import ast
import sys
from pathlib import Path


class StaticMethodFixer(ast.NodeVisitor):
    """Find and fix @staticmethod methods that still have self parameter."""

    def __init__(self, filepath):
        self.filepath = filepath
        self.fixes = []
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

        # Check if has @staticmethod decorator
        has_staticmethod = False
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name) and decorator.id == "staticmethod":
                has_staticmethod = True
                break

        if has_staticmethod and node.args.args:
            first_arg = node.args.args[0].arg
            if first_arg in ("self", "cls"):
                self.fixes.append(
                    {
                        "class": self.current_class,
                        "method": node.name,
                        "line": node.lineno,
                        "first_arg": first_arg,
                    }
                )


def find_fixes_in_file(filepath):
    """Find methods that need fixing in a file."""
    try:
        with open(filepath, "r") as f:
            source = f.read()
        tree = ast.parse(source, filename=str(filepath))
        fixer = StaticMethodFixer(filepath)
        fixer.visit(tree)
        return fixer.fixes
    except Exception as e:
        print(f"Error processing {filepath}: {e}", file=sys.stderr)
        return []


def fix_file(filepath, fixes):
    """Remove self/cls from @staticmethod methods."""
    with open(filepath, "r") as f:
        lines = f.readlines()

    modified = 0
    for fix in fixes:
        line_idx = fix["line"] - 1
        line = lines[line_idx]
        param = fix["first_arg"]

        # Remove 'self, ' or 'cls, ' from the signature
        if f"{param}, " in line:
            lines[line_idx] = line.replace(f"{param}, ", "", 1)
            modified += 1
        # Handle case where it's the only parameter: (self)
        elif f"({param})" in line:
            lines[line_idx] = line.replace(f"({param})", "()", 1)
            modified += 1

    with open(filepath, "w") as f:
        f.writelines(lines)

    return modified


def main():
    """Main function."""
    root = Path("fc_selector")

    all_fixes = []
    by_file = {}

    for py_file in sorted(root.rglob("*.py")):
        fixes = find_fixes_in_file(py_file)
        if fixes:
            by_file[py_file] = fixes
            all_fixes.extend(fixes)

    if not all_fixes:
        print("No fixes needed!")
        return 0

    print(f"\nFound {len(all_fixes)} methods to fix in {len(by_file)} files\n")

    total_modified = 0
    for filepath, fixes in sorted(by_file.items()):
        print(f"Processing {filepath} ({len(fixes)} methods)...")
        modified = fix_file(filepath, fixes)
        total_modified += modified

    print(f"\n✅ Fixed {total_modified} method signatures")
    return 0


if __name__ == "__main__":
    sys.exit(main())

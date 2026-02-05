#!/usr/bin/env python3
"""
Script to automatically add @staticmethod decorators to methods that don't use self.
Uses pylint to identify candidates.
"""

import re
import subprocess
import sys
from pathlib import Path


def get_pylint_r0201_issues():
    """Run pylint to find all R0201 issues."""
    print("Running pylint to find R0201 issues...")

    # Run pylint with only R0201 enabled
    result = subprocess.run(
        ["pylint", "--disable=all", "--enable=R0201", "--output-format=json", "fc_selector"],
        capture_output=True,
        text=True,
    )

    if not result.stdout:
        print("No R0201 issues found or pylint failed")
        return []

    import json
    issues = json.loads(result.stdout)

    # Filter for R0201 (no-self-use)
    r0201_issues = [i for i in issues if i.get("message-id") == "R0201"]

    print(f"Found {len(r0201_issues)} R0201 issues")
    return r0201_issues


def group_issues_by_file(issues):
    """Group issues by file path."""
    by_file = {}
    for issue in issues:
        path = issue["path"]
        if path not in by_file:
            by_file[path] = []
        by_file[path].append(issue)
    return by_file


def add_staticmethod_decorator(file_path, line_number):
    """Add @staticmethod decorator to a method at the given line."""
    with open(file_path, "r") as f:
        lines = f.readlines()

    # Find the actual method definition line (might be different due to decorators)
    target_line = line_number - 1  # Convert to 0-indexed

    # Look backwards to find where to insert @staticmethod
    insert_line = target_line

    # Skip backwards over existing decorators
    while insert_line > 0:
        line = lines[insert_line - 1].strip()
        if line.startswith("@") or line == "":
            insert_line -= 1
        else:
            break

    # Get indentation from the def line
    def_line = lines[target_line]
    indentation = len(def_line) - len(def_line.lstrip())
    indent_str = " " * indentation

    # Check if @staticmethod already exists
    for i in range(insert_line, target_line):
        if "@staticmethod" in lines[i]:
            return False  # Already has decorator

    # Insert @staticmethod
    lines.insert(insert_line, f"{indent_str}@staticmethod\n")

    with open(file_path, "w") as f:
        f.writelines(lines)

    return True


def main():
    """Main function."""
    # Get all R0201 issues
    issues = get_pylint_r0201_issues()

    if not issues:
        print("No issues to fix!")
        return 0

    # Group by file
    by_file = group_issues_by_file(issues)

    print(f"\nFound issues in {len(by_file)} files")

    # Process each file
    fixed_count = 0
    for file_path, file_issues in sorted(by_file.items()):
        print(f"\nProcessing {file_path} ({len(file_issues)} issues)...")

        # Sort by line number (descending) to avoid line number shifts
        file_issues.sort(key=lambda x: x["line"], reverse=True)

        for issue in file_issues:
            line = issue["line"]
            symbol = issue.get("symbol", "")
            message = issue.get("message", "")

            print(f"  Line {line}: {message}")

            if add_staticmethod_decorator(file_path, line):
                fixed_count += 1

    print(f"\n✅ Added @staticmethod to {fixed_count} methods")
    return 0


if __name__ == "__main__":
    sys.exit(main())

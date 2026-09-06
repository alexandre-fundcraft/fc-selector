#!/usr/bin/env python3
"""Turn the salvaged .pyc files into something a human can read.

Python 3.11 has no working decompiler, but a .pyc still carries the module and
function docstrings, every signature, and all string constants — which for a
code generator is where the templates live. That is enough to rebuild from.

Usage:  python salvage/extract.py
Writes: salvage/extracted/<module>.md
"""

from __future__ import annotations

import marshal
import types
from pathlib import Path

HERE = Path(__file__).parent
BYTECODE = HERE / "bytecode"
OUT = HERE / "extracted"

# .pyc layout for 3.7+: 16-byte header, then the marshalled code object.
HEADER = 16


def load(pyc: Path) -> types.CodeType:
    return marshal.loads(pyc.read_bytes()[HEADER:])


def docstring(code: types.CodeType) -> str:
    first = code.co_consts[0] if code.co_consts else None
    return first if isinstance(first, str) else ""


def signature(code: types.CodeType) -> str:
    args = list(code.co_varnames[: code.co_argcount])
    if code.co_flags & 0x04:
        args.append("*args")
    if code.co_flags & 0x08:
        args.append("**kwargs")
    return f"{code.co_name}({', '.join(args)})"


def children(code: types.CodeType) -> list[types.CodeType]:
    return [c for c in code.co_consts if isinstance(c, types.CodeType)]


def constants(code: types.CodeType, seen: set[int], out: list[tuple[str, str]]) -> None:
    """Collect string constants that look like content rather than plumbing."""
    for const in code.co_consts:
        if isinstance(const, types.CodeType):
            constants(const, seen, out)
        elif isinstance(const, str) and const != docstring(code):
            if (len(const) > 20 or "\n" in const) and id(const) not in seen:
                seen.add(id(const))
                out.append((code.co_name, const))


def render(code: types.CodeType, depth: int = 1) -> list[str]:
    lines = []
    for child in children(code):
        if child.co_name in {"<listcomp>", "<genexpr>", "<dictcomp>", "<setcomp>", "<lambda>"}:
            continue
        prefix = "  " * (depth - 1)
        lines.append(f"{prefix}- `{signature(child)}`")
        doc = docstring(child)
        if doc:
            summary = " ".join(doc.split())
            lines.append(f"{prefix}  > {summary[:300]}")
        lines += render(child, depth + 1)
    return lines


def main() -> None:
    OUT.mkdir(exist_ok=True)
    index = []

    for pyc in sorted(BYTECODE.glob("*.pyc")):
        module = pyc.name.split(".")[0]
        code = load(pyc)

        body = [f"# `{module}`", ""]
        doc = docstring(code)
        if doc:
            body += ["## Module docstring", "", "```", doc.strip(), "```", ""]

        api = render(code)
        if api:
            body += ["## API surface", "", *api, ""]

        strings: list[tuple[str, str]] = []
        constants(code, set(), strings)
        if strings:
            body += ["## String constants", "", "Templates and messages, in definition order.", ""]
            for owner, value in strings:
                body += [f"### in `{owner}`", "", "```", value, "```", ""]

        (OUT / f"{module}.md").write_text("\n".join(body) + "\n")
        index.append((module, len(api), len(strings)))
        print(f"{module:28s} {len(api):3d} api entries  {len(strings):3d} strings")

    print(f"\n{len(index)} modules -> {OUT}")


if __name__ == "__main__":
    main()

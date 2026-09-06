# Salvaged pre-git modules

Compiled bytecode for 16 modules that existed in this project **before it was
put under version control**, recovered from `fc_selector/__pycache__/` on
2026-09-06. No `.py` source for any of them exists in any commit.

They are kept here because `make clean` deletes `__pycache__`, and these files
were the only surviving copy.

## What happened

| When | What |
| --- | --- |
| Oct–Nov 2025 | The library has a flat layout: `fc_selector/filter_parser.py`, `mixins.py`, `optimization.py`, `repository.py`, `selector_code_generator.py`, … Code generation works: `manage.py generate_odata_selector` produces DTOs and selectors from Django models. |
| Nov–Dec 2025 | The package is restructured into `core/`, `django/`, `protocols/`, and renamed from `django_odata` to `fc_selector`. |
| 2025-12-22 | First commit (`7617db2`) captures the restructured tree. The generator modules are **not** included — but `fc_selector/management/commands/` is, still importing `fc_selector.dependency_detector`, `fc_selector.selector_code_generator` and `fc_selector.introspection`. |
| — | `manage.py generate_odata_selector` therefore raises `ModuleNotFoundError` from the very first commit. It never ran from this repository. |
| 2026-02-11 | `fd47bb2` removes the broken command shell ("dead management commands"). The documentation that describes the generator is left behind. |

The salvaged templates still emit `from django_odata.django.selector import
ODataSelector`, which dates them to before the rename and confirms the timeline.

## Contents

- `bytecode/` — the 16 `.pyc` files, untouched. Python 3.11 (magic `a70d0d0a`).
- `extracted/` — one Markdown file per module: module docstring, every function
  signature, every docstring, and all string constants.
- `extract.py` — regenerates `extracted/` from `bytecode/`.

## Why not just decompile it

No decompiler supports Python 3.11 bytecode: `uncompyle6` and `decompyle3` stop
at 3.8, and `pycdc` is partial. But a `.pyc` keeps docstrings, signatures and
string constants, and for a code generator the string constants *are* the
templates. `extract.py` pulls those out, which is enough to rebuild from.

## The generator, if it is ever rebuilt

`selector_code_generator` (22 API entries, 51 string constants) is the core:

- `generate_dto_fields(fields, relationships, model_class)`
- `generate_dto_class(model_class, fields, relationships, models_in_file)`
- `generate_selector_expandable_fields(relationships, exclude_edges, app_label)`
- `generate_selector_class(model_class, app_label, relationships, exclude_edges)`
- `generate_selector_file(...)` and `format_python_code(code)`

supported by `introspection` (model metadata) and `dependency_detector`
(which relationships become `expandable_fields`, and which edges to cut so
DTO cycles terminate).

Note that these templates target the **November 2025 API**: the flat module
layout, and DTOs and selectors as they were before `QueryIntent` and before the
2026-09 audit. The recoverable value is the design — what to introspect, which
functions are needed, how cycles are cut — not the template strings verbatim.

Rebuilding is a project with its own spec, not a `git revert`.

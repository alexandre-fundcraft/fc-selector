"""
Django management command for Auto-Generate OData Selectors with DTOs.

Usage:
    python manage.py generate_odata_selector blog.BlogPost
    python manage.py generate_odata_selector --app blog
    python manage.py generate_odata_selector --app blog --single
    python manage.py generate_odata_selector --app blog --single --force

Options:
    --single   Generate one combined file instead of separate files per model
    --force    Overwrite existing files without prompting for confirmation
    --output   Specify custom output directory for generated selectors
"""

from datetime import datetime
from pathlib import Path

from django.apps import apps

from fc_selector.dependency_detector import should_include_relationship
from fc_selector.selector_code_generator import (
    format_python_code,
    generate_selector_file,
)

from ._base import BaseODataGeneratorCommand


class Command(BaseODataGeneratorCommand):
    """Management command to auto-generate OData Selectors with DTOs from Django models."""

    help = "Auto-generate ODataSelector subclasses with DTOs from Django models"
    artifact_name = "selector"
    output_folder = "selectors"

    def _generate_all_codes(
        self, all_model_info: dict, excluded_edges: set, models_in_file: set, options: dict
    ) -> dict:
        """Generate selector code for all models."""
        selector_codes = {}

        for model_path, model_data in all_model_info.items():
            model = model_data["model"]
            info = model_data["info"]
            app_config = apps.get_app_config(model._meta.app_label)
            app_label = app_config.name

            # Filter relationships to exclude circular ones
            filtered_relationships = [
                rel
                for rel in info["relationships"]
                if should_include_relationship(model_path, rel.related_model, excluded_edges)
            ]

            code = generate_selector_file(
                model,
                app_label,
                info["fields"],
                filtered_relationships,
                excluded_edges,
                single=options.get("single", False),
                models_in_file=models_in_file,
            )
            code = format_python_code(code)
            selector_codes[model_path] = code

        return selector_codes

    def _write_files(
        self,
        selector_codes: dict[str, str],
        output_dir: Path,
        single: bool,
        force: bool,
        requested_options: dict,
    ):
        """Write selector code to files."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        if single:
            primary_app = output_dir.parent.name
            combined_code = self._combine_selectors(selector_codes, primary_app)

            requested_model_name = self._get_requested_model_name(requested_options)
            if requested_model_name:
                file_name = self._camel_to_snake(requested_model_name) + ".py"
            else:
                first_model_path = next(iter(selector_codes.keys()))
                primary_model_name = first_model_path.split(".")[-1]
                file_name = self._camel_to_snake(primary_model_name) + ".py"

            output_file = output_dir / file_name
            self._write_file_with_overwrite_check(output_file, combined_code, force)

            actual_filename = file_name[:-3]
            self._generate_init_file(output_dir, selector_codes.keys(), single, actual_filename)
        else:
            for model_path, code in selector_codes.items():
                model_name = model_path.split(".")[-1]
                file_name = self._camel_to_snake(model_name) + ".py"
                output_file = output_dir / file_name
                self._write_file_with_overwrite_check(output_file, code, force)

            self._generate_init_file(output_dir, selector_codes.keys(), single, None)

    def _generate_init_file(self, output_dir: Path, model_paths, single: bool, primary_model_name=None):
        """Generate __init__.py with imports for selectors and DTOs."""
        imports = []

        if single:
            primary_file_name = primary_model_name if primary_model_name else "blog_post"
            for model_path in model_paths:
                model_name = model_path.split(".")[-1]
                selector_name = f"{model_name}Selector"
                dto_name = f"{model_name}DTO"
                imports.append(f"from .{primary_file_name} import {selector_name}, {dto_name}")
        else:
            for model_path in model_paths:
                model_name = model_path.split(".")[-1]
                selector_name = f"{model_name}Selector"
                dto_name = f"{model_name}DTO"
                file_name = self._camel_to_snake(model_name)
                imports.append(f"from .{file_name} import {selector_name}, {dto_name}")

        init_file = output_dir / "__init__.py"
        init_file.write_text("\n".join(imports) + "\n")

    def _combine_selectors(self, selector_codes: dict[str, str], primary_app: str) -> str:
        """Combine multiple selector codes into one file with deduplicated imports."""
        import re

        model_info = {}
        for model_path in selector_codes.keys():
            app_label, model_name = model_path.split(".")
            model_info[model_path] = {"app_label": app_label, "model_name": model_name}

        imports = [
            "from __future__ import annotations  # Enable forward references",
            "",
            "from dataclasses import dataclass",
            "from typing import Optional, List",
            "from django.apps import apps",
            "",
            "from django_odata.core.dtos import BaseODataDTO, UNSET",
            "from django_odata.django.selector import ODataSelector",
            "",
        ]

        model_imports = []
        for model_path, info in model_info.items():
            model_app = info["app_label"]
            model_name = info["model_name"]
            model_imports.append(f"{model_name} = apps.get_model('{model_app}', '{model_name}')")

        model_imports.sort()

        dto_dict = {}
        dto_dependencies = {}
        selector_definitions = []

        for model_path, code in selector_codes.items():
            model_name = model_path.split(".")[-1]

            dto_start = code.find("# ==================== DTOs ====================")
            selector_start = code.find("# ==================== SELECTORS ====================")

            if dto_start != -1 and selector_start != -1:
                dto_section = code[dto_start:selector_start].strip()
                dto_section = dto_section.replace("# ==================== DTOs ====================", "").strip()

                selector_section = code[selector_start:].strip()
                selector_section = selector_section.replace(
                    "# ==================== SELECTORS ====================", ""
                ).strip()

                if dto_section:
                    dto_dict[model_name] = dto_section

                    dependencies = []
                    for line in dto_section.split("\n"):
                        if "Optional[" in line and "DTO]" in line:
                            matches = re.findall(r"Optional\[(\w+DTO)\]", line)
                            dependencies.extend(matches)
                        elif "Optional[List[" in line and "DTO]]" in line:
                            matches = re.findall(r"Optional\[List\[(\w+DTO)\]\]", line)
                            dependencies.extend(matches)

                    dto_name = f"{model_name}DTO"
                    dependencies = [d.replace("DTO", "") for d in dependencies if d != dto_name]
                    dto_dependencies[model_name] = dependencies

                if selector_section:
                    selector_definitions.append(selector_section)

        sorted_models = self._topological_sort(dto_dict, dto_dependencies)
        dto_definitions = [dto_dict[model] for model in sorted_models]

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        header = f'''"""
Auto-generated OData selectors and DTOs (combined file).
Generated on: {now}

DO NOT EDIT THIS FILE MANUALLY.
Regenerate using: python manage.py generate_odata_selector --single

Available options:
  --single   Generate one combined file instead of separate files
  --force    Overwrite existing files without prompting
"""

'''

        combined = (
            header
            + "\n".join(imports)
            + "\n".join(model_imports)
            + "\n\n\n# ==================== DTOs ====================\n\n"
            + "\n\n".join(dto_definitions)
            + "\n\n\n# ==================== SELECTORS ====================\n\n"
            + "\n\n".join(selector_definitions)
        )

        return combined

    @staticmethod
    def _topological_sort(dto_dict: dict, dto_dependencies: dict) -> list:
        """Sort DTOs so dependencies come before dependents."""
        sorted_models = []
        visited = set()
        visiting = set()

        def visit(model):
            if model in visited:
                return
            if model in visiting:
                return

            visiting.add(model)

            for dep in dto_dependencies.get(model, []):
                if dep in dto_dict:
                    visit(dep)

            visiting.remove(model)
            visited.add(model)
            sorted_models.append(model)

        for model in dto_dict.keys():
            visit(model)

        return sorted_models

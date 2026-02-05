"""
Django management command for Auto-Generate OData Serializers.

Usage:
    python manage.py generate_odata_serializer blog.BlogPost
    python manage.py generate_odata_serializer --app blog
    python manage.py generate_odata_serializer --app blog --single
    python manage.py generate_odata_serializer --app blog --single --force

Options:
    --single   Generate one combined file instead of separate files per model
    --force    Overwrite existing files without prompting for confirmation
    --output   Specify custom output directory for generated serializers
"""

from datetime import datetime
from pathlib import Path

from django.apps import apps

from fc_selector.code_generator import (
    format_python_code,
    generate_serializer_class,
)
from fc_selector.dependency_detector import should_include_relationship

from ._base import BaseODataGeneratorCommand


class Command(BaseODataGeneratorCommand):
    """Management command to auto-generate OData serializers from Django models."""

    help = "Auto-generate ODataModelSerializer subclasses from Django models"
    artifact_name = "serializer"
    output_folder = "serializers"

    def _generate_all_codes(
        self, all_model_info: dict, excluded_edges: set, models_in_file: set, options: dict
    ) -> dict:
        """Generate serializer code for all models."""
        serializer_codes = {}

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

            code = generate_serializer_class(
                model,
                app_label,
                info["fields"],
                filtered_relationships,
                excluded_edges,
                single=options.get("single", False),
                models_in_file=models_in_file,
            )
            code = format_python_code(code)
            serializer_codes[model_path] = code

        return serializer_codes

    def _write_files(
        self,
        serializer_codes: dict[str, str],
        output_dir: Path,
        single: bool,
        force: bool,
        requested_options: dict,
    ):
        """Write serializer code to files."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        if single:
            primary_app = output_dir.parent.name
            combined_code = self._combine_serializers(serializer_codes, primary_app)

            requested_model_name = self._get_requested_model_name(requested_options)
            if requested_model_name:
                file_name = self._camel_to_snake(requested_model_name) + ".py"
            else:
                first_model_path = next(iter(serializer_codes.keys()))
                primary_model_name = first_model_path.split(".")[-1]
                file_name = self._camel_to_snake(primary_model_name) + ".py"

            output_file = output_dir / file_name
            self._write_file_with_overwrite_check(output_file, combined_code, force)

            actual_filename = file_name[:-3]
            self._generate_init_file(output_dir, serializer_codes.keys(), single, actual_filename)
        else:
            for model_path, code in serializer_codes.items():
                model_name = model_path.split(".")[-1]
                file_name = self._camel_to_snake(model_name) + ".py"
                output_file = output_dir / file_name
                self._write_file_with_overwrite_check(output_file, code, force)

            self._generate_init_file(output_dir, serializer_codes.keys(), single, None)

    def _generate_init_file(self, output_dir: Path, model_paths, single: bool, primary_model_name=None):
        """Generate __init__.py with imports for serializers."""
        imports = []

        if single:
            primary_file_name = primary_model_name if primary_model_name else "blog_post"
            for model_path in model_paths:
                model_name = model_path.split(".")[-1]
                serializer_name = f"{model_name}Serializer"
                imports.append(f"from .{primary_file_name} import {serializer_name}")
        else:
            for model_path in model_paths:
                model_name = model_path.split(".")[-1]
                serializer_name = f"{model_name}Serializer"
                file_name = self._camel_to_snake(model_name)
                imports.append(f"from .{file_name} import {serializer_name}")

        init_file = output_dir / "__init__.py"
        init_file.write_text("\n".join(imports) + "\n")

    def _combine_serializers(self, serializer_codes: dict[str, str], primary_app: str) -> str:
        """Combine multiple serializer codes into one file with deduplicated imports."""
        model_info = self._extract_model_info(serializer_codes)
        imports = self._collect_imports(model_info, primary_app)
        class_definitions = self._extract_class_definitions(serializer_codes)
        header = self._generate_header()

        sorted_imports = sorted(imports)
        combined = header + "\n".join(sorted_imports) + "\n\n\n" + "\n\n\n".join(class_definitions)

        return combined

    def _extract_model_info(self, serializer_codes: dict[str, str]) -> dict:
        """Extract model information from serializer code keys."""
        model_info = {}
        for model_path in serializer_codes.keys():
            app_label, model_name = model_path.split(".")
            model_info[model_path] = {"app_label": app_label, "model_name": model_name}
        return model_info

    def _collect_imports(self, model_info: dict, primary_app: str) -> set[str]:
        """Collect and deduplicate imports for the combined serializer file."""
        imports = {"from django_odata.serializers import ODataModelSerializer"}

        for model_path, info in model_info.items():
            model_app = info["app_label"]
            model_name = info["model_name"]
            import_statement = self._get_model_import(model_app, model_name, primary_app)
            imports.add(import_statement)

        return imports

    def _get_model_import(self, model_app: str, model_name: str, primary_app: str) -> str:
        """Generate the import statement for a model."""
        if model_app == primary_app:
            return f"from ..models import {model_name}"

        app_module_map = {
            "auth": "django.contrib.auth",
            "contenttypes": "django.contrib.contenttypes",
            "sessions": "django.contrib.sessions",
            "messages": "django.contrib.messages",
            "admin": "django.contrib.admin",
            "sites": "django.contrib.sites",
        }
        full_app_path = app_module_map.get(model_app, model_app)
        return f"from {full_app_path}.models import {model_name}"

    def _extract_class_definitions(self, serializer_codes: dict[str, str]) -> list[str]:
        """Extract class definitions from serializer code, skipping imports and docstrings."""
        class_definitions = []

        for model_path, code in serializer_codes.items():
            lines = code.split("\n")
            code_start = self._skip_docstring(lines)
            class_code = self._extract_class_from_lines(lines[code_start:])

            if class_code:
                class_definitions.append(class_code)

        return class_definitions

    def _skip_docstring(self, lines: list[str]) -> int:
        """Find the line index where code starts after skipping the module docstring."""
        in_docstring = False
        code_start = 0

        for i, line in enumerate(lines):
            if line.strip().startswith('"""'):
                if not in_docstring:
                    in_docstring = True
                elif line.strip().endswith('"""') and len(line.strip()) > 3:
                    code_start = i + 1
                    break
                elif line.strip() == '"""':
                    code_start = i + 1
                    break
            elif not in_docstring:
                code_start = i
                break

        return code_start

    def _extract_class_from_lines(self, lines: list[str]) -> str:
        """Extract class definition from lines, skipping import statements."""
        current_class = []

        for line in lines:
            line = line.rstrip()
            if line.startswith("from ") or line.startswith("import "):
                continue
            elif line.startswith("class ") or current_class:
                current_class.append(line)
            elif line.strip() == "" and current_class:
                break

        return "\n".join(current_class) if current_class else ""

    def _generate_header(self) -> str:
        """Generate the file header with timestamp and usage instructions."""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f'''"""
Auto-generated OData serializers (combined file).
Generated on: {now}

DO NOT EDIT THIS FILE MANUALLY.
Regenerate using: python manage.py generate_odata_serializer --single

Available options:
  --single   Generate one combined file instead of separate files
  --force    Overwrite existing files without prompting
"""

'''

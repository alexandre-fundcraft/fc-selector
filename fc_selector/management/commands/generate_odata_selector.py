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

import re
from pathlib import Path

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError

from fc_selector.dependency_detector import (
    build_relationship_graph,
    detect_cycles,
    resolve_circular_dependencies,
    should_include_relationship,
)
from fc_selector.introspection import get_all_model_info
from fc_selector.selector_code_generator import (
    format_python_code,
    generate_selector_file,
)


class Command(BaseCommand):
    """Management command to auto-generate OData Selectors with DTOs from Django models."""

    help = "Auto-generate ODataSelector subclasses with DTOs from Django models"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "models",
            nargs="*",
            help="Model paths in format app_label.ModelName (e.g., blog.BlogPost)",
        )
        parser.add_argument(
            "--app",
            action="append",
            dest="apps",
            help="Generate selectors for all models in specified app",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite existing files without prompting",
        )
        parser.add_argument(
            "--single",
            action="store_true",
            help="Generate one combined file instead of separate files",
        )
        parser.add_argument(
            "--output",
            type=str,
            help="Custom output directory for generated selectors",
        )

    def handle(self, *args, **options):
        """Main command handler."""
        models_to_generate = []
        output_dir = None

        # Discover models
        if options.get("apps"):
            for app_label in options["apps"]:
                try:
                    app_config = apps.get_app_config(app_label)
                    models_to_generate.extend(app_config.get_models())
                    if not output_dir:
                        # Default output directory is app's selectors folder
                        app_path = Path(app_config.module.__file__).parent
                        output_dir = app_path / "selectors"
                except LookupError:
                    raise CommandError(f"App '{app_label}' not found")
        elif options.get("models"):
            for model_path in options["models"]:
                model = self._load_model_from_path(model_path)
                models_to_generate.append(model)
                if not output_dir:
                    # Default output directory is app's selectors folder
                    app_label = model._meta.app_label
                    app_config = apps.get_app_config(app_label)
                    app_path = Path(app_config.module.__file__).parent
                    output_dir = app_path / "selectors"
        else:
            raise CommandError("Please specify models or use --app flag to specify an app")

        # Override output directory if specified
        if options.get("output"):
            output_dir = Path(options["output"])

        # Remove duplicates
        models_to_generate = list(set(models_to_generate))

        # If using --single, discover all related models for expandable_fields
        if options.get("single", False):
            models_to_generate = self._discover_related_models(models_to_generate)

        self.stdout.write(self.style.SUCCESS(f"Generating selectors for {len(models_to_generate)} model(s)..."))

        # Get model info
        all_model_info = {}
        relationships_map = {}

        for model in models_to_generate:
            model_path = f"{model._meta.app_label}.{model.__name__}"
            info = get_all_model_info(model)
            all_model_info[model_path] = {
                "model": model,
                "info": info,
            }
            relationships_map[model_path] = info["relationships"]

        # Detect circular dependencies
        graph = build_relationship_graph(models_to_generate, relationships_map)
        cycles = detect_cycles(graph)
        excluded_edges = resolve_circular_dependencies(cycles)

        if cycles:
            self.stdout.write(
                self.style.WARNING(
                    f"Detected {len(cycles)} circular dependenc(ies). Will skip some reverse relationships."
                )
            )
            for cycle in cycles:
                self.stdout.write(self.style.WARNING(f"  Cycle: {' -> '.join(cycle.cycle)}"))

        # Generate selectors
        selector_codes = {}
        # In single mode, collect all model paths being generated for direct references
        models_in_file = set()
        if options.get("single", False):
            for model_path, model_data in all_model_info.items():
                app_config = apps.get_app_config(model_data["model"]._meta.app_label)
                full_path = f"{app_config.name}.{model_data['model'].__name__}"
                models_in_file.add(full_path)

        for model_path, model_data in all_model_info.items():
            model = model_data["model"]
            info = model_data["info"]
            # Get the full app name from AppConfig instead of just app_label
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

        # Write files
        self._write_selector_files(
            selector_codes,
            output_dir,
            single=options.get("single", False),
            force=options.get("force", False),
            requested_options=options,
        )

        self.stdout.write(
            self.style.SUCCESS(f"Successfully generated {len(selector_codes)} selector(s) in {output_dir}")
        )

    def _load_model_from_path(self, model_path: str):
        """Load a Django model from app_label.ModelName format.

        Args:
            model_path: Model path like 'blog.BlogPost'

        Returns:
            Django model class

        Raises:
            CommandError: If model not found
        """
        try:
            app_label, model_name = model_path.split(".")
            model = apps.get_model(app_label, model_name)
            return model
        except (ValueError, LookupError):
            raise CommandError(f"Model '{model_path}' not found")

    def _write_selector_files(
        self,
        selector_codes: dict[str, str],
        output_dir: Path,
        single: bool,
        force: bool,
        requested_options=None,
    ):
        """Write selector code to files.

        Args:
            selector_codes: Dict mapping model paths to selector code
            output_dir: Output directory path
            single: Whether to combine all selectors into one file
            force: Whether to overwrite existing files without prompting
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        primary_model_name = None

        if single:
            # Determine primary app from output directory
            primary_app = output_dir.parent.name

            # Combine all selectors into one file with deduplicated imports
            combined_code = self._combine_selectors(selector_codes, primary_app)

            # Use the originally requested model name for the filename
            requested_model_name = None
            if requested_options.get("models"):
                # Get the first requested model
                requested_model_path = requested_options["models"][0]
                requested_model_name = requested_model_path.split(".")[-1]
            elif requested_options.get("apps"):
                # If using --app, use the first model from the first app
                app_label = requested_options["apps"][0]
                try:
                    app_config = apps.get_app_config(app_label)
                    first_model = app_config.get_models()[0]
                    requested_model_name = first_model.__name__
                except (LookupError, IndexError):
                    requested_model_name = None

            if requested_model_name:
                file_name = self._camel_to_snake(requested_model_name) + ".py"
            else:
                # Fallback to first model in dict
                first_model_path = next(iter(selector_codes.keys()))
                primary_model_name = first_model_path.split(".")[-1]
                file_name = self._camel_to_snake(primary_model_name) + ".py"

            output_file = output_dir / file_name

            self._write_file_with_overwrite_check(output_file, combined_code, force)
        else:
            # Write one file per model
            for model_path, code in selector_codes.items():
                model_name = model_path.split(".")[-1]
                # Convert CamelCase to snake_case
                file_name = self._camel_to_snake(model_name) + ".py"
                output_file = output_dir / file_name
                self._write_file_with_overwrite_check(output_file, code, force)

        # Generate __init__.py
        if single:
            # For single mode, pass the actual filename used (without .py extension)
            actual_filename = file_name[:-3]  # Remove .py extension
            self._generate_init_file(output_dir, selector_codes.keys(), single, actual_filename)
        else:
            self._generate_init_file(output_dir, selector_codes.keys(), single, None)

    def _write_file_with_overwrite_check(self, output_file: Path, content: str, force: bool):
        """Write file with overwrite check unless force is True.

        Args:
            output_file: Path to the output file
            content: Content to write
            force: Whether to overwrite without prompting
        """
        if output_file.exists() and not force:
            response = input(f"File {output_file} already exists. Overwrite? [y/N]: ")
            if response.lower() not in ("y", "yes"):
                self.stdout.write(self.style.WARNING(f"  Skipped {output_file}"))
                return

        output_file.write_text(content)
        self.stdout.write(self.style.SUCCESS(f"  Written to {output_file}"))

    def _generate_init_file(self, output_dir: Path, model_paths, single: bool, primary_model_name=None):
        """Generate __init__.py with imports.

        Args:
            output_dir: Output directory path
            model_paths: Iterable of model paths
            single: Whether selectors are combined into one file
            primary_model_name: Primary model name for single file naming
        """
        imports = []

        if single:
            # Import all selectors and DTOs from the primary model file
            primary_file_name = primary_model_name if primary_model_name else "blog_post"
            for model_path in model_paths:
                model_name = model_path.split(".")[-1]
                selector_name = f"{model_name}Selector"
                dto_name = f"{model_name}DTO"
                imports.append(f"from .{primary_file_name} import {selector_name}, {dto_name}")
        else:
            # Import each selector and DTO from its own file
            for model_path in model_paths:
                model_name = model_path.split(".")[-1]
                selector_name = f"{model_name}Selector"
                dto_name = f"{model_name}DTO"
                file_name = self._camel_to_snake(model_name)
                imports.append(f"from .{file_name} import {selector_name}, {dto_name}")

        init_file = output_dir / "__init__.py"
        init_file.write_text("\n".join(imports) + "\n")

    @staticmethod
    def _camel_to_snake(name: str) -> str:
        """Convert CamelCase to snake_case.

        Args:
            name: CamelCase string

        Returns:
            snake_case string
        """
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

    def _discover_related_models(self, initial_models: list) -> list:
        """Discover all related models needed for expandable_fields when using --single.

        Args:
            initial_models: List of initially requested models

        Returns:
            List of models including all related models for expandable_fields
        """
        discovered_models = set(initial_models)
        models_to_process = list(initial_models)

        while models_to_process:
            current_model = models_to_process.pop(0)

            # Get model info to find relationships
            model_info = get_all_model_info(current_model)

            for relationship in model_info["relationships"]:
                # Parse the related model path
                try:
                    # Split and get the model name (last part) and app name (everything before)
                    parts = relationship.related_model.split(".")
                    related_model_name = parts[-1]
                    related_app_name = ".".join(parts[:-1])

                    # To get the model, we need the app_label (e.g., 'blog'), not the full app name
                    try:
                        related_model = apps.get_model(related_app_name, related_model_name)
                    except LookupError:
                        # If that fails, try with just the app_label (last part of the app name)
                        related_app_label = parts[-2] if len(parts) > 1 else parts[0]
                        related_model = apps.get_model(related_app_label, related_model_name)

                    # If this is a new model, add it to be processed
                    if related_model not in discovered_models:
                        discovered_models.add(related_model)
                        models_to_process.append(related_model)

                except (ValueError, LookupError) as e:
                    # Skip if related model cannot be found
                    self.stdout.write(
                        self.style.WARNING(f"Could not load related model {relationship.related_model}: {e}")
                    )
                    continue

        self.stdout.write(
            self.style.SUCCESS(
                f"Discovered {len(discovered_models) - len(initial_models)} additional related model(s) for --single mode"
            )
        )

        return list(discovered_models)

    def _combine_selectors(self, selector_codes: dict[str, str], primary_app: str) -> str:
        """Combine multiple selector codes into one file with deduplicated imports.

        Args:
            selector_codes: Dict mapping model paths to selector code

        Returns:
            Combined selector code with single header and deduplicated imports
        """
        from datetime import datetime

        # Collect all the models
        model_info = {}
        for model_path in selector_codes.keys():
            app_label, model_name = model_path.split(".")
            model_info[model_path] = {"app_label": app_label, "model_name": model_name}

        # Standard imports
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

        # Import ALL models that have selectors being generated
        model_imports = []
        for model_path, info in model_info.items():
            model_app = info["app_label"]
            model_name = info["model_name"]
            model_imports.append(f"{model_name} = apps.get_model('{model_app}', '{model_name}')")

        # Sort model imports for consistency
        model_imports.sort()

        # Extract DTOs and Selectors from each file
        dto_dict = {}  # model_name -> dto_code
        dto_dependencies = {}  # model_name -> [dependency_names]
        selector_definitions = []

        for model_path, code in selector_codes.items():
            model_name = model_path.split(".")[-1]

            # Split code into sections
            dto_section = ""
            selector_section = ""

            # Find DTO section
            dto_start = code.find("# ==================== DTOs ====================")
            selector_start = code.find("# ==================== SELECTORS ====================")

            if dto_start != -1 and selector_start != -1:
                # Extract DTO section (between DTO marker and SELECTOR marker)
                dto_section = code[dto_start:selector_start].strip()
                # Remove the marker line
                dto_section = dto_section.replace("# ==================== DTOs ====================", "").strip()

                # Extract Selector section (after SELECTOR marker)
                selector_section = code[selector_start:].strip()
                # Remove the marker line
                selector_section = selector_section.replace(
                    "# ==================== SELECTORS ====================", ""
                ).strip()

                if dto_section:
                    dto_dict[model_name] = dto_section

                    # Extract dependencies (other DTOs referenced in this DTO)
                    dependencies = []
                    for line in dto_section.split("\n"):
                        if "Optional[" in line and "DTO]" in line:
                            # Find DTO reference like: Optional[AuthorDTO]
                            import re

                            matches = re.findall(r"Optional\[(\w+DTO)\]", line)
                            dependencies.extend(matches)
                        elif "Optional[List[" in line and "DTO]]" in line:
                            # Find DTO reference like: Optional[List[CategoryDTO]]
                            matches = re.findall(r"Optional\[List\[(\w+DTO)\]\]", line)
                            dependencies.extend(matches)

                    # Remove self-references and convert to model names
                    dto_name = f"{model_name}DTO"
                    dependencies = [d.replace("DTO", "") for d in dependencies if d != dto_name]
                    dto_dependencies[model_name] = dependencies

                if selector_section:
                    selector_definitions.append(selector_section)

        # Topological sort DTOs based on dependencies
        def topological_sort(dto_dict, dto_dependencies):
            """Sort DTOs so dependencies come before dependents."""
            sorted_models = []
            visited = set()
            visiting = set()

            def visit(model):
                if model in visited:
                    return
                if model in visiting:
                    # Circular dependency detected, skip
                    return

                visiting.add(model)

                # Visit dependencies first
                for dep in dto_dependencies.get(model, []):
                    if dep in dto_dict:  # Only visit if we have this DTO
                        visit(dep)

                visiting.remove(model)
                visited.add(model)
                sorted_models.append(model)

            # Visit all DTOs
            for model in dto_dict.keys():
                visit(model)

            return sorted_models

        sorted_models = topological_sort(dto_dict, dto_dependencies)
        dto_definitions = [dto_dict[model] for model in sorted_models]

        # Generate combined file header
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

        # Combine everything
        # Note: Sentinel (UNSET) is now imported from django_odata.core.dtos
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

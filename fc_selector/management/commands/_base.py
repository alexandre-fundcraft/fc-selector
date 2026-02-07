"""
Base class for OData code generation management commands.

This module provides the shared functionality for generating OData selectors
and serializers from Django models.
"""

import re
from abc import abstractmethod
from pathlib import Path

from django.apps import apps
from django.core.management.base import BaseCommand, CommandError

from fc_selector.dependency_detector import (
    build_relationship_graph,
    detect_cycles,
    resolve_circular_dependencies,
)
from fc_selector.introspection import get_all_model_info


class BaseODataGeneratorCommand(BaseCommand):
    """Base class for OData code generation commands.

    Subclasses must implement:
        - artifact_name: Name of the artifact being generated (e.g., "selector", "serializer")
        - output_folder: Name of the output folder (e.g., "selectors", "serializers")
        - generate_code: Method to generate the code for a model
        - write_files: Method to write the generated code to files
    """

    # To be defined by subclasses
    artifact_name: str = ""
    output_folder: str = ""

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
            help=f"Generate {self.artifact_name}s for all models in specified app",
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
            help=f"Custom output directory for generated {self.artifact_name}s",
        )

    def handle(self, *args, **options):
        """Main command handler."""
        models_to_generate, output_dir = self._discover_models(options)

        # If using --single, discover all related models for expandable_fields
        if options.get("single", False):
            models_to_generate = self._discover_related_models(models_to_generate)

        self.stdout.write(
            self.style.SUCCESS(f"Generating {self.artifact_name}s for {len(models_to_generate)} model(s)...")
        )

        # Get model info and relationships
        all_model_info, relationships_map = BaseODataGeneratorCommand._get_model_info(models_to_generate)

        # Detect and handle circular dependencies
        excluded_edges = self._handle_circular_dependencies(models_to_generate, relationships_map)

        # Collect models in file for single mode
        models_in_file = BaseODataGeneratorCommand._collect_models_in_file(all_model_info, options)

        # Generate code for each model
        generated_codes = BaseODataGeneratorCommand._generate_all_codes(all_model_info, excluded_edges, models_in_file, options)

        # Write files
        self._write_files(
            generated_codes,
            output_dir,
            single=options.get("single", False),
            force=options.get("force", False),
            requested_options=options,
        )

        self.stdout.write(
            self.style.SUCCESS(f"Successfully generated {len(generated_codes)} {self.artifact_name}(s) in {output_dir}")
        )

    def _discover_models(self, options) -> tuple[list, Path | None]:
        """Discover models to generate code for.

        Args:
            options: Command options dictionary

        Returns:
            Tuple of (models_to_generate, output_dir)

        Raises:
            CommandError: If no models or apps specified
        """
        models_to_generate = []
        output_dir: Path | None = None

        if options.get("apps"):
            for app_label in options["apps"]:
                try:
                    app_config = apps.get_app_config(app_label)
                    models_to_generate.extend(app_config.get_models())
                    if not output_dir:
                        app_path = Path(app_config.module.__file__).parent
                        output_dir = app_path / self.output_folder
                except LookupError as exc:
                    raise CommandError(f"App '{app_label}' not found") from exc
        elif options.get("models"):
            for model_path in options["models"]:
                model = BaseODataGeneratorCommand._load_model_from_path(model_path)
                models_to_generate.append(model)
                if not output_dir:
                    app_label = model._meta.app_label  # noqa: W0212 - Django's public API
                    app_config = apps.get_app_config(app_label)
                    app_path = Path(app_config.module.__file__).parent
                    output_dir = app_path / self.output_folder
        else:
            raise CommandError("Please specify models or use --app flag to specify an app")

        # Override output directory if specified
        if options.get("output"):
            output_dir = Path(options["output"])

        # Remove duplicates
        models_to_generate = list(set(models_to_generate))

        return models_to_generate, output_dir

    @staticmethod
    def _load_model_from_path(model_path: str):
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
        except (ValueError, LookupError) as exc:
            raise CommandError(f"Model '{model_path}' not found") from exc

    @staticmethod
    def _get_model_info(models: list) -> tuple[dict, dict]:
        """Get model info and relationships for all models.

        Args:
            models: List of Django model classes

        Returns:
            Tuple of (all_model_info, relationships_map)
        """
        all_model_info = {}
        relationships_map = {}

        for model in models:
            model_path = f"{model._meta.app_label}.{model.__name__}"  # noqa: W0212 - Django's public API
            info = get_all_model_info(model)
            all_model_info[model_path] = {
                "model": model,
                "info": info,
            }
            relationships_map[model_path] = info["relationships"]

        return all_model_info, relationships_map

    def _handle_circular_dependencies(self, models: list, relationships_map: dict) -> set:
        """Detect and handle circular dependencies.

        Args:
            models: List of Django model classes
            relationships_map: Dict mapping model paths to relationships

        Returns:
            Set of excluded edges to break circular dependencies
        """
        graph = build_relationship_graph(models, relationships_map)
        cycles = detect_cycles(graph)
        excluded_edges: set = resolve_circular_dependencies(cycles)

        if cycles:
            self.stdout.write(
                self.style.WARNING(
                    f"Detected {len(cycles)} circular dependenc(ies). Will skip some reverse relationships."
                )
            )
            for cycle in cycles:
                self.stdout.write(self.style.WARNING(f"  Cycle: {' -> '.join(cycle.cycle)}"))

        return excluded_edges

    @staticmethod
    def _collect_models_in_file(all_model_info: dict, options: dict) -> set:
        """Collect model paths for single mode.

        Args:
            all_model_info: Dict mapping model paths to model data
            options: Command options dictionary

        Returns:
            Set of model paths in the file (empty if not single mode)
        """
        models_in_file = set()
        if options.get("single", False):
            for _, model_data in all_model_info.items():
                app_config = apps.get_app_config(model_data["model"]._meta.app_label)  # noqa: W0212 - Django's public API
                full_path = f"{app_config.name}.{model_data['model'].__name__}"
                models_in_file.add(full_path)
        return models_in_file

    @staticmethod
    @abstractmethod
    def _generate_all_codes(
        all_model_info: dict, excluded_edges: set, models_in_file: set, options: dict
    ) -> dict:
        """Generate code for all models.

        Args:
            all_model_info: Dict mapping model paths to model data
            excluded_edges: Set of excluded edges for circular dependencies
            models_in_file: Set of model paths in the file
            options: Command options dictionary

        Returns:
            Dict mapping model paths to generated code
        """
        pass

    @abstractmethod
    def _write_files(
        self,
        generated_codes: dict[str, str],
        output_dir: Path,
        single: bool,
        force: bool,
        requested_options: dict,
    ):
        """Write generated code to files.

        Args:
            generated_codes: Dict mapping model paths to generated code
            output_dir: Output directory path
            single: Whether to combine all into one file
            force: Whether to overwrite existing files without prompting
            requested_options: Original command options
        """
        pass

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
                    parts = relationship.related_model.split(".")
                    related_model_name = parts[-1]
                    related_app_name = ".".join(parts[:-1])

                    # Try with the full name first, then fall back to just the last part
                    try:
                        related_model = apps.get_model(related_app_name, related_model_name)
                    except LookupError:
                        related_app_label = parts[-2] if len(parts) > 1 else parts[0]
                        related_model = apps.get_model(related_app_label, related_model_name)

                    # If this is a new model, add it to be processed
                    if related_model not in discovered_models:
                        discovered_models.add(related_model)
                        models_to_process.append(related_model)

                except (ValueError, LookupError) as e:
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

    @staticmethod
    def _get_requested_model_name(requested_options: dict) -> str | None:
        """Get the name of the originally requested model for filename.

        Args:
            requested_options: Original command options

        Returns:
            Model name or None
        """
        if requested_options.get("models"):
            requested_model_path: str = requested_options["models"][0]
            return requested_model_path.split(".")[-1]
        if requested_options.get("apps"):
            app_label: str = requested_options["apps"][0]
            try:
                app_config = apps.get_app_config(app_label)
                first_model = app_config.get_models()[0]
                return str(first_model.__name__)
            except (LookupError, IndexError):
                return None
        return None

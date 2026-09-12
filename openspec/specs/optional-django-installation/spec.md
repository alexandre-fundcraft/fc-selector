# optional-django-installation Specification

## Purpose
Keep the framework-neutral query core usable without Django while providing an explicit, independently verified Django installation extra.

## Requirements

### Requirement: Base package is independently installable
Installing the base wheel MUST NOT install Django, Django REST Framework or drf-spectacular. Core fluent queries, generic DTO projection and OData parsing MUST work in that environment.
#### Scenario: Base wheel in an isolated environment
- **WHEN** a consumer installs the wheel without extras
- **THEN** adapter packages are absent and core/protocol operations succeed without importing the source tree

### Requirement: Django extra and development dependencies are complete
The Django extra MUST include Django, Django REST Framework and drf-spectacular. Development dependencies MUST provide the adapter without a self-dependency. Documentation MUST list all three extra dependencies.
#### Scenario: Development installation
- **WHEN** a contributor synchronizes the dev group
- **THEN** all adapter requirements are installed without the project listing itself as a dependency

### Requirement: Isolation checks cover all adapter imports
Core isolation tests MUST reject imports of Django, Django REST Framework and drf-spectacular.
#### Scenario: Accidental spectacular import
- **WHEN** core code attempts to import drf_spectacular during the probe
- **THEN** the test fails

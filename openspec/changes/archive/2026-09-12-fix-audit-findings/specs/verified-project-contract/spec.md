## Purpose

Keep the public documentation and metadata aligned with supported behavior and enforce reproducible quality checks.

## ADDED Requirements

### Requirement: Metadata describes exposed fields
Metadata MUST use exposed DTO fields and API aliases and MUST omit protected or disallowed fields rather than advertise every model column.

#### Scenario: Aliased projected DTO
- **WHEN** a selector exposes an aliased subset of model fields
- **THEN** metadata describes that subset with the API-facing names

### Requirement: Documented commands exist
Getting-started instructions MUST NOT require absent generator or seed commands. Documentation MUST describe low-level versus collection pagination and hybrid fallbacks accurately.

#### Scenario: Fresh setup
- **WHEN** a developer follows the quickstart
- **THEN** they can define a DTO and selector without an unavailable management command

### Requirement: Quality checks block failures
Lint and type-check commands MUST fail on errors. CI MUST run tests, lint and type checks. The existing no-migrations test configuration MUST remain unchanged.

#### Scenario: Invalid code
- **WHEN** lint or type checking reports an error
- **THEN** the quality gate exits unsuccessfully

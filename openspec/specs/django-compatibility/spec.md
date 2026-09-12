# django-compatibility Specification

## Purpose
Define supported Python and Django combinations and require portable ORM execution verified by an explicit compatibility matrix.

## Requirements

### Requirement: Not-equal filters compile across tested frameworks
Not-equal filters MUST execute correctly on each explicitly tested Django version, independent of whether compiled SQL parameters are lists or tuples.
#### Scenario: Mixed parameter containers
- **WHEN** the left and right SQL operands return different sequence container types
- **THEN** compilation preserves both parameter sequences in order without a server error

### Requirement: Explicit compatibility verification
CI MUST identify the Python and Django combinations it tests, including the minimum declared Django version and representative newer release lines. Documentation MUST distinguish verified database backends from unverified ones.
#### Scenario: Framework compatibility run
- **WHEN** a matrix test job starts
- **THEN** it verifies the intended Django release line rather than relying on the default lock resolution alone

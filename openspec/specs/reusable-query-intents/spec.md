# reusable-query-intents Specification

## Purpose
Provide detached, reusable query intents and a single execution preparation contract while keeping core query construction and projection independent of protocols and ORMs.

## Requirements

### Requirement: Query execution preserves caller state
Executing or validating a query MUST NOT modify caller-owned query intents, including nested projections. Reusing the same query with another selector MUST apply that selector's own policies.
#### Scenario: Reuse a wildcard projection
- **WHEN** a wildcard query is executed by selectors with different allowed fields
- **THEN** each result follows its own policy and the original wildcard remains unchanged

### Requirement: Builder representations preserve public behavior
Replacing or combining textual and fluent options MUST preserve their meaning without stale options. Building an intent MUST return detached state. Textual options MUST retain lazy filter parsing; fluent options that cannot be exported MUST fail explicitly.
#### Scenario: Replace fluent options with text
- **WHEN** fluent filter, expansion and ordering are replaced with textual options
- **THEN** only the replacement options affect the built query
#### Scenario: Modify a built query
- **WHEN** a caller modifies a previously built nested intent
- **THEN** subsequent builds remain unchanged

### Requirement: Equivalent materialization paths
Equivalent textual and fluent queries MUST return equivalent DTO and dictionary projections in standard and optimized modes, including nested restrictions and pagination, without per-row SQL growth.
#### Scenario: Forward expansion parity
- **WHEN** multiple rows are projected with an expanded forward relation through each public materialization path
- **THEN** fields, values and ordering agree and SQL count does not grow per row

### Requirement: ORM-independent query and projection contracts
Neutral query construction and generic DTO projection MUST work without an installed ORM or a loaded query-language parser. Protocol parsing MUST produce the same neutral intent consumed by ORM adapters. Existing Django and textual compatibility entry points MUST remain usable.
#### Scenario: Fluent query without ORM or protocol parser
- **WHEN** a consumer constructs and builds a neutral fluent query with ORM and OData imports unavailable
- **THEN** construction succeeds and returns a neutral intent
#### Scenario: Generic nested projection
- **WHEN** DTO projection receives plain objects with list-valued relations
- **THEN** it projects values without requiring Django managers or prefetch caches
#### Scenario: OData parsing without Django
- **WHEN** a consumer parses an OData query without Django available
- **THEN** parsing returns a neutral intent without loading an ORM adapter

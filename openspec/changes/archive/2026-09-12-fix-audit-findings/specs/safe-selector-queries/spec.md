## Purpose

Ensure selector requests preserve their meaning while enforcing field, authorization, pagination and serialization boundaries.

## ADDED Requirements

### Requirement: Sensitive fields remain private
Responses MUST omit password, DTO-excluded and serializer write-only fields, including nested objects. Explicit nested serializer policies SHALL be honored.

#### Scenario: Nested user and write-only field
- **WHEN** a response expands a user or includes a write-only field
- **THEN** protected values are absent at every affected depth

### Requirement: Object authorization and query scoping
API reads MUST honor view query scoping and filter backends. Retrieval MUST check object permissions against the model before DTO projection. Counts MUST use the same scope as results.

#### Scenario: Denied object
- **WHEN** object permission denies a matching model
- **THEN** retrieval returns a permission error without serialized data

### Requirement: Query composition preserves conditions
Combining fluent and textual filters MUST preserve their Boolean meaning. Primary-key lookup MUST constrain the actual primary key, including string keys, without string interpolation.

#### Scenario: Fluent filter followed by textual condition
- **WHEN** a textual ID condition is appended to a fluent filter
- **THEN** only rows satisfying both conditions are returned

### Requirement: Consistent validation and decoding
Field selection, filtering, ordering and expansion MUST enforce configured policies before execution in both modes. URL values MUST be decoded exactly once. Invalid query syntax or fields MUST produce controlled client errors.

#### Scenario: Restricted field or malformed request
- **WHEN** a request uses a forbidden field, unknown field, invalid nested option or malformed expression
- **THEN** it fails with a client error rather than executing unchecked or returning a server error

#### Scenario: Encoded literals
- **WHEN** a literal contains plus, ampersand or percent characters
- **THEN** its original value is preserved

### Requirement: Bounded collection reads
Collection materialization helpers MUST apply selector default and maximum limits, including requests with only an offset. Count operations MUST not count only a page. Pagination links MUST reflect the effective page size and preserve encoded parameters; zero-sized pages MUST not loop.

#### Scenario: Offset-only collection request
- **WHEN** a request specifies an offset but no limit
- **THEN** the configured default limit still applies

### Requirement: Equivalent expansion semantics
String and fluent queries and standard and hybrid execution MUST preserve nested selection, filtering, ordering and expansion. Child pagination MUST apply independently per parent. Omitting a primary key from projection MUST NOT remove expanded children. Many-to-many output MUST retain requested order.

#### Scenario: Two parents with limited children
- **WHEN** two parents each have children and one child per parent is requested
- **THEN** each parent's collection contains its own first matching child

#### Scenario: Expansion without selected primary key
- **WHEN** a projection omits the parent ID and expands children
- **THEN** children are attached while the parent ID remains omitted

### Requirement: Standard expansion avoids deferred-field N+1
Expanding a forward relation with scalar DTO fields MUST NOT cause extra scalar fetches per parent.

#### Scenario: Three roots with a forward relation
- **WHEN** standard execution serializes three roots and one expanded forward relation
- **THEN** root scalar fields are fetched in the main query, not six additional queries

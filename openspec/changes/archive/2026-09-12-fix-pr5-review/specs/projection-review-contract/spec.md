## ADDED Requirements

### Requirement: Nested projection preserves scoped aliases
DTO projection SHALL preserve field aliases configured on each expanded relation without importing ORM or protocol modules into core.

#### Scenario: Aliased child field
- **WHEN** an expansion selects display mapped to the child's name
- **THEN** dictionary and DTO results contain display with the actual child value, for singular and collection relations

### Requirement: Dictionary projection supports properties
Dictionary materialization SHALL fall back to model projection for requested DTO properties.

#### Scenario: Selected model property
- **WHEN** a dictionary query selects a DTO field backed by a model property
- **THEN** it returns the computed value rather than silently omitting the field, regardless of values_mode

### Requirement: Related paths are validated before evaluation
The executor SHALL reject nonexistent relationship segments or terminal fields with InvalidFieldError while retaining valid relations, properties and annotations.

#### Scenario: Missing related field
- **WHEN** a selection requests target/missing
- **THEN** preparation raises InvalidFieldError before SQL evaluation, including with allowed_fields configured

### Requirement: Retrieve errors have meaningful regression coverage
Tests SHALL inject failures into actual retrieve execution stages and assert their specific mapped OData exceptions.

#### Scenario: Invalid field during preparation
- **WHEN** executor preparation raises InvalidFieldError
- **THEN** retrieve raises ODataFieldNotFoundError with the original cause

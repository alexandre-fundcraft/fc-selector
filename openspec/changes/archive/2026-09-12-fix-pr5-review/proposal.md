## Why
PR 5 review identified missing nested aliases, property loss in dictionary projection, incomplete relation path validation, stale exception mocks and contradictory hybrid documentation.

## What Changes
- Carry plain alias mapping trees into neutral DTO recursion.
- Fall back to model projection for dictionary properties.
- Validate relation segments and preserve explicit annotation support.
- Correct retrieve error tests and hybrid documentation.

## Capabilities
### New Capabilities
- `projection-review-contract`: consistent projection and controlled related-field validation.

### Modified Capabilities
None.

## Impact
Core DTO projection, Django executor/selector/visitor, regression tests and concepts documentation. No ORM dependency added to core. No API format changes or SQLAlchemy implementation.

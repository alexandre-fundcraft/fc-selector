## 1. Compatibility
- [x] 1.1 Add failing SQL parameter regression and fix not-equal lookup.
## 2. Execution boundaries
- [x] 2.1 Add intent reuse/non-mutation regressions and centralize preparation with pure validation.
- [x] 2.2 Select execution mode once and preserve direct builder compatibility and DRF projection.
## 3. Builder and behavior contracts
- [x] 3.1 Consolidate QueryBuilder representations, preserving lazy parsing and public methods; test replacement, composition and detached builds.
- [x] 3.2 Move shared DTOs/selectors to support and add textual/fluent, standard/hybrid, DTO/dict parity tests with SQL bounds.
## 4. Architectural boundaries
- [x] 4.1 Isolate protocol-specific builder parsing/export behind compatibility entry points; neutral fluent state depends only on core.
- [x] 4.2 Isolate Django path translation and relation extraction from generic DTO projection, retaining legacy behavior.
- [x] 4.3 Add import-boundary and plain-object projection tests; document core/protocol/ORM dependency direction and remaining compatibility surfaces.
## 5. Compatibility verification
- [x] 5.1 Define explicit Python/Django CI matrix and document verified backend/version scope.
- [x] 5.2 Run complete regression suite, lint, types, strict docs and OpenSpec; record evidence.

# CodeLoom — Self-Contained Developer Documentation

**Status:** Current-state documentation generated from the supplied repository snapshot and project documentation.  
**Verification scope:** static reconciliation of supplied source/tree/documentation; runtime execution must still be performed before treating every claim as verified.

## Product

CodeLoom is an AI-assisted accessibility engineering system built around:

```text
Live URL
  -> Playwright + axe-core
  -> runtime findings
  -> deterministic clustering
  -> GitHub repository + pinned commit
  -> TypeScript/JSX AST source intelligence
  -> source mapping
  -> patch generation
  -> deterministic validation
  -> candidate workspace / sandbox
  -> Playwright + axe re-scan
  -> regression comparison
  -> GitHub PR
```

Core thesis:

> **Fix the source, not the symptoms.**

## Read this documentation in order

1. `PROJECT_STATE.md`
2. `SYSTEM_ARCHITECTURE.md`
3. `PROJECT_STRUCTURE.md`
4. `DEVELOPER_SETUP.md`
5. `RUNTIME_SCAN.md`
6. `SOURCE_INTELLIGENCE.md`
7. `PATCH_PIPELINE.md`
8. `GITHUB_INTEGRATION.md`
9. `FRONTEND.md`
10. `API_REFERENCE.md`
11. `DATA_MODELS.md`
12. `TESTING_VERIFICATION.md`
13. `SECURITY.md`
14. `KNOWN_LIMITATIONS.md`
15. `AI_AGENT_CONTEXT.md`
16. `RELEASE_CHECKLIST.md`

## Trust rule

Code > tests > runtime observation > current documentation > historical documentation.

The repository contains multiple development eras. Never treat an old audit as current runtime truth without checking the actual code.


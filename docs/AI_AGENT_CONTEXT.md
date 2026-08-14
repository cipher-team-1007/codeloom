# CodeLoom — AI Coding Agent Context

## Mission

Help developers fix accessibility problems at the source while preserving deterministic safety.

## Architecture

```text
Python FastAPI master
    +
Node TypeScript AST microservice
    +
frontend
```

## Product principle

> Fix the source, not the symptoms.

## Golden workflow

```text
URL
 -> Playwright/Axe
 -> cluster
 -> GitHub
 -> pinned commit
 -> AST source mapping
 -> patch
 -> deterministic validation
 -> sandbox/re-scan
 -> verified
 -> PR
```

## Preserve

- Python orchestration
- Playwright/Axe runtime scanner
- deterministic clustering
- commit pinning
- Node AST boundary
- evidence provenance
- deterministic validator
- GitHub server-side security

## Never

- create a second master backend;
- reintroduce regex as authoritative source mapping;
- let LLM choose authoritative source identity;
- call simulation VERIFIED;
- expose secrets to frontend;
- silently relax safety checks;
- delete tests to obtain a green result.

## Coding workflow

Before editing:

1. read implementation;
2. read relevant tests;
3. trace caller;
4. run smallest relevant test;
5. make smallest correct change;
6. rerun tests;
7. run dependent regression;
8. update docs.

## Source mapping rule

Only deterministic evidence can establish source identity.

If uncertain:

```text
AMBIGUOUS
```

and stop automatic patching.

## Patch rule

AI proposes.

Validator decides whether patch is structurally safe.

Sandbox/re-scan decides runtime outcome.

Developer decides publication.

## Documentation rule

When code and docs disagree:

```text
code + tests + runtime
```

win.

Mark older documents as historical rather than copying stale claims forward.


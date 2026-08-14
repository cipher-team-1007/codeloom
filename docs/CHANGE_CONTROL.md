# CodeLoom — Documentation Change Control

## Purpose

The repository has multiple historical implementation streams. Documentation drift is therefore a major risk.

## Status labels

Use:

```text
CURRENT
HISTORICAL
EXPERIMENTAL
PROPOSED
DEPRECATED
```

## Every major architecture doc

Include:

```text
Status:
Last verified:
Verified against:
```

## Update rules

When changing runtime architecture update:

- `SYSTEM_ARCHITECTURE.md`
- `PROJECT_STATE.md`
- `PROJECT_STRUCTURE.md`
- `AI_AGENT_CONTEXT.md`

When changing source mapping update:

- `SOURCE_INTELLIGENCE.md`
- `PATCH_PIPELINE.md`
- tests

When changing GitHub publication update:

- `GITHUB_INTEGRATION.md`
- `SECURITY.md`

When changing API update:

- `API_REFERENCE.md`
- frontend integration docs
- data model docs

## No unsupported claims

Do not use:

```text
100% precise
VERIFIED
production-ready
zero regressions
real sandbox
exact source
```

unless actual implementation/test evidence supports the claim.


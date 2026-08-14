# CodeLoom — Patch Pipeline

## Governing principle

> AI proposes. Deterministic systems validate. The sandbox proves. The developer approves.

## Pipeline

```text
Runtime cluster
 -> source mapping
 -> ContextPack
 -> patch plan
 -> deterministic or AI proposal
 -> patch candidate
 -> validation
 -> conflict detection
 -> candidate workspace
 -> sandbox/re-scan
 -> fingerprint comparison
 -> VERIFIED
```

## ContextPack

The LLM should receive only relevant context:

```text
repository + commit
target file
target node
target range
before/source code
surrounding code
symbol/component
imports/usages
route context
related nodes
runtime findings
source findings
framework/package context
```

Never send the whole repository by default.

## AI boundary

AI proposes:

- explanation
- remediation
- before/after candidate
- patch candidate

Deterministic systems decide:

- source identity
- repository/commit
- exact patch target
- syntax validity
- verification result
- regression status

## Validation

Required checks include:

1. repository identity
2. commit match
3. file exists
4. allowed extension
5. source fingerprint
6. exact before-code match
7. line/range validity
8. diff-size cap
9. syntax parse
10. AST validity
11. safety guard
12. conflict check

Occurrence rule:

```text
0 matches -> reject
1 match  -> candidate
>1 matches -> reject/require disambiguation
```

## Unified diff

Generate from actual file state.

Preferred:

```bash
git diff
```

or a standards-compliant diff library.

Never construct a fake diff by prefixing every old line with `-` and every new line with `+`.

## Stale source

Before applying:

```text
verified commit
+
current workspace commit
+
source fingerprint
```

must agree.

Otherwise:

```text
BASE_COMMIT_STALE
SOURCE_CHANGED
```

## Candidate workspace

Always use an isolated copy.

Never modify the source snapshot used for comparison.

## Verification

A genuine `VERIFIED` state requires evidence that:

- patch applied;
- syntax parsed;
- application started;
- target loaded;
- Playwright/axe re-scan completed;
- target findings resolved;
- no regression fingerprints appeared.

If the current sandbox only simulates DOM behavior, label the output `SIMULATED`.

## Publication

Only `VERIFIED` candidates may reach the GitHub publisher.


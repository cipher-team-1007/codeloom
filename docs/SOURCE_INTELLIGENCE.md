# CodeLoom — Source Intelligence

## Purpose

Map runtime evidence to source-code locations using deterministic AST evidence.

## Service

```text
services/source-intelligence/
```

Technology:

- Node.js
- Fastify
- TypeScript
- TypeScript Compiler API

## Service responsibilities

```text
repositoryPath
commitSha
runtimeEvidence
    |
    v
AST parser
    |
    v
source index
    |
    v
candidate generator
    |
    v
candidate scoring
    |
    v
ambiguity analysis
    |
    v
mapping result
```

## Source node

A useful indexed node contains:

```json
{
  "nodeId": "node_123",
  "filePath": "src/components/ProductCard.tsx",
  "nodeKind": "JSXElement",
  "symbol": "ProductCard",
  "startLine": 14,
  "endLine": 18,
  "startByte": 300,
  "endByte": 470,
  "contentHash": "sha256..."
}
```

## Matching evidence

Prefer deterministic signals:

- element/tag match
- class match
- literal attribute match
- structural parent context
- stable IDs
- rendered/source snippet similarity where defensible
- component identity

Do not call a mapping exact simply because `ruleId` matches.

## Match states

```text
MATCHED
AMBIGUOUS
NOT_FOUND
```

If the service cannot confidently identify one source location:

```text
do not auto-patch
```

## Security

All paths must resolve beneath the allowed repository root.

Reject:

- `../`
- absolute paths
- null bytes
- drive-letter escapes
- symlink escapes

## Python integration

Python client:

```text
backend/engine/source_intelligence/client.py
```

## Source fixtures

Use:

```text
experiments/source-mapping/
```

for:

- multiline JSX
- repeated components
- dynamic props
- duplicate classes
- ambiguous candidates
- exact patch-target regression tests


# Source Intelligence Service

> **Canonical System Reference**: [`docs/ACCESSIFIX_PROJECT_BIBLE.md`](file:///c:/Users/kunal/Downloads/lexical%20ai%20-%20parmarth/lexical-ai/docs/ACCESSIFIX_PROJECT_BIBLE.md)  
> **PDF Version Available**: [`docs/ACCESSIFIX_PROJECT_BIBLE.pdf`](file:///c:/Users/kunal/Downloads/lexical%20ai%20-%20parmarth/lexical-ai/docs/ACCESSIFIX_PROJECT_BIBLE.pdf)  

## Purpose
The Source Intelligence Service is a dedicated Node.js microservice within the AccessiFix architecture. It takes a minified runtime accessibility HTML snippet (e.g., from Playwright/Axe-core) and maps it back to the exact static TSX/JSX source component file that generated it. 

It accomplishes this by leveraging the native TypeScript Compiler API to extract deterministic structural tokens (tags, literal attributes, CSS classes, dynamic expression headers) from the source repository, and heuristically scoring them against the runtime evidence.

## Non-Purpose
This service is strictly a deterministic static analyzer. It DOES NOT:
- Execute Playwright or scan URLs.
- Group or cluster findings.
- Download or clone GitHub repositories.
- Use LLMs or generate code patches.
- Verify patches in a sandbox.

## Architecture
This service acts as an HTTP REST backend intended to be called by the master Python orchestrator (`backend`). The Python engine provides the repository path and runtime evidence, and this Node.js service returns the matching candidates.

## API

### `POST /v1/source-mappings`
Accepts a mapping request and returns ranked source candidates.

**Request:**
```json
{
  "repositoryPath": "/absolute/path/to/cloned/repo",
  "commitSha": "a1b2c3d...",
  "runtimeEvidence": {
  "ruleId": "image-alt",
  "targetSelector": "img.product-image",
  "htmlSnippet": "<img class=\"product-image\" src=\"/img.jpg\">"
  }
}
```

**Response:**
```json
{
  "status": "MATCHED", // Or AMBIGUOUS, NOT_FOUND
  "findingId": "image-alt",
  "candidates": [
  {
    "file": "/absolute/path/to/cloned/repo/src/components/ProductCard.tsx",
    "component": "ProductCard",
    "element": "img",
    "sourceRange": {
    "start": { "line": 15, "column": 5 }
    },
    "score": 3,
    "signals": [
    "+ tag match: img",
    "+ class match: product-image"
    ]
  }
  ],
  "parserMetadata": {
  "filesScanned": 0,
  "elementsIndexed": 14
  }
}
```

### `GET /health`
Returns basic service health.

## Local Development
```bash
npm install
npm run dev
```

## Testing
```bash
npm run test
```

## Security
This service treats repository code as completely untrusted. It:
1. Validates that the requested `repositoryPath` resides within the configured `SOURCE_REPOSITORY_ROOT`.
2. NEVER executes or imports the target source code. It only passes strings into the TS Compiler API AST generator.
3. Contains no LLM logic, completely isolating the matching process from prompt-injection risks in the target codebase.

## Limitations
- **Cross-Component Abstraction:** Elements that exclusively use spread props (e.g., `<img {...props} />`) without any static CSS classes or literal attributes are difficult to match reliably and may result in a `NOT_FOUND` or low score.
- **Identical Components:** If a repository contains two distinct components with identical static signatures (e.g., `<img className="generic" src={src} />`), the service correctly bails out and returns `AMBIGUOUS` rather than guessing. Deeper DOM tree traversal is required to break ties.
- **Commit SHA Verification:** Not fully enforced locally unless git executable bounds checking is implemented.


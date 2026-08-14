# CodeLoom — System Architecture

## Architecture boundary

```text
          FRONTEND
           |
           v
    +----------------------------+
    | Python FastAPI Master      |
    | backend/engine             |
    +-------------+--------------+
            |
    +-------------+--------------+
    |             |              |
    v             v              v
   Runtime Scan   Repository     AI/Patch
   Playwright     Acquisition    Generation
   + axe          + snapshots    + validation
    |             |
    |             v
    |       SourceIntel Client
    |             |
    |       localhost:8001
    |             v
    |     Node/Fastify Service
    |     TypeScript Compiler API
    |             |
    |       AST Parse/Index
    |             |
    +------+------+
         |
         v
    Root Cause Evidence
         |
         v
      Patch Candidate
         |
         v
     Deterministic Validator
         |
         v
    Candidate Workspace
         |
         v
     Sandbox / Browser Re-scan
         |
         v
      Verification
         |
         v
     GitHub Publisher
```

## Python master engine responsibilities

- HTTP API
- Playwright/Axe scanning
- custom accessibility/SEO/performance analysis
- finding normalization
- deduplication
- clustering
- repository acquisition
- source-intelligence client
- AI context/prompt orchestration
- patch validation
- sandbox orchestration
- telemetry
- queues
- GitHub authentication/publication
- persistence

## Node source-intelligence responsibilities

- parse TypeScript/TSX/JSX/HTML
- build source indexes
- identify candidate source nodes
- score runtime-to-source matches
- return explicit ambiguity/not-found states
- enforce repository-root security

It must not become a second master backend.

## Service ports

Documented local configuration:

```text
Python/FastAPI: 8000
Node/source-intelligence: 8001
```

## Authority model

```text
Scanner
  -> Clusterer
  -> Source mapper
  -> AI proposer
  -> Deterministic validator
  -> Sandbox
  -> Verification authority
```

The LLM is never the authority for:

- source identity
- repository identity
- commit identity
- verification status
- regression status
- PR authorization

## State model

A remediation workflow should distinguish:

```text
CREATED
ACQUIRING
MAPPING
PLANNING
GENERATING
VALIDATING
APPLYING
VERIFYING
VERIFIED
FAILED
AMBIGUOUS
STALE
REGRESSION
```

Never collapse these into a single boolean.

## Evidence chain

Every result should retain provenance:

```text
runtime finding
  -> cluster
  -> source match
  -> patch
  -> validation
  -> verification
```


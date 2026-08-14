# CodeLoom — Testing and Verification

## Python tests

The snapshot contains:

```text
tests/test_phase4_backend.py
tests/test_phase5_ai.py
tests/test_v1_pipeline.py
tests/checkpoints/
tests/integration/
tests/unit/
```

## Checkpoint runner

Documented:

```bash
cd backend
python -c "import sys; sys.stdout.reconfigure(encoding='utf-8'); import tests.checkpoints.check_all as c; c.main()"
```

Checkpoints cover:

- models/mock data
- deduplication
- clustering
- knowledge
- specialists
- orchestrator
- simulator
- API
- scanner
- storage

## Integration areas

The tree includes integration tests for:

- GitHub
- batch publishing
- live GitHub
- master workflow
- queues
- orchestrator source mapping
- repository acquisition
- sandbox executor
- source-intelligence client
- LLM patch generator
- SSE

## Node tests

```text
services/source-intelligence/tests/integration/source-mapping.test.ts
```

## Golden fixture

Use:

```text
experiments/source-mapping/fixture/
```

and demonstrate:

```text
runtime issue
 -> one cluster
 -> exact source candidate
 -> patch
 -> diff
 -> validation
 -> verification
```

## Negative tests

Must include:

- SSRF
- path traversal
- ambiguous source
- missing source
- stale commit
- duplicate beforeCode
- invalid syntax
- oversized patch
- conflict
- sandbox failure
- unresolved target finding
- regression
- malformed AI output
- prompt injection

## Release rule

A green unit suite is necessary but not sufficient.

Also execute:

- build/typecheck;
- API smoke test;
- browser E2E;
- source-intelligence E2E;
- GitHub/public-repo smoke test;
- failure injection;
- manual UX walk-through.


# CodeLoom — API Reference

This snapshot contains multiple historical API paths. The actual FastAPI OpenAPI schema is the final authority.

## Documented master endpoints

```http
GET  /health
POST /api/v1/remediations/workflow
GET  /api/v1/remediations/{workflow_id}/events
```

## Findings/clusters

Documented historical endpoint:

```http
GET /api/scans/{scanId}/clusters
```

## Fixes

Documented historical endpoint:

```http
POST /api/clusters/{clusterId}/generate-fix
POST /api/fixes/{fixId}/simulate
```

## GitHub

The codebase contains GitHub authorization/callback/status/disconnect routes and publisher endpoints.

## Source intelligence

The Node service contains source-mapping routes. Inspect `services/source-intelligence/src/routes/` for exact current path and schema.

## API reconciliation rule

Do not maintain two API references by hand.

Before release:

```text
GET /openapi.json
```

and inspect FastAPI's registered routes.

The generated OpenAPI contract should be copied/reconciled into this document.

## Frontend rule

Frontend API calls must import the canonical API base from one configuration location. Do not scatter hard-coded ports across files.


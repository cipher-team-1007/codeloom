# CodeLoom — Release Checklist

## Architecture

- [ ] One canonical Python master engine.
- [ ] One dedicated Node source-intelligence service.
- [ ] No legacy Express backend in launch path.
- [ ] One canonical frontend.

## Runtime

- [ ] URL validation tested.
- [ ] SSRF protections tested.
- [ ] Playwright scan tested.
- [ ] axe tested.
- [ ] custom analyzers tested.
- [ ] clustering deterministic.

## Source

- [ ] GitHub acquisition works.
- [ ] commit pinning works.
- [ ] AST parsing works.
- [ ] source mapping works on fixture.
- [ ] ambiguity is safe.

## Patch

- [ ] context generated deterministically.
- [ ] AI output schema validated.
- [ ] exact target validated.
- [ ] stale source rejected.
- [ ] real unified diff generated.
- [ ] conflict checks pass.
- [ ] candidate workspace isolated.

## Verification

- [ ] sandbox behavior verified.
- [ ] Playwright re-scan real if labeled verified.
- [ ] target fingerprints resolved.
- [ ] regression fingerprints zero.
- [ ] no false VERIFIED states.

## GitHub

- [ ] credentials server-side.
- [ ] remote branch SHA rechecked.
- [ ] PR disabled before VERIFIED.
- [ ] PR generated from verified patch.

## Frontend

- [ ] clear start point.
- [ ] no dead buttons.
- [ ] no fake values.
- [ ] no fake progress.
- [ ] no implementation jargon in primary workflow.
- [ ] no console errors.
- [ ] no critical network failures.

## Documentation

- [ ] docs match current code.
- [ ] historical docs identified.
- [ ] simulated behavior explicitly labeled.
- [ ] setup commands verified.
- [ ] API docs reconciled against OpenAPI.


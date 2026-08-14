# CodeLoom — Frontend

## Current supplied files

```text
index.html
audit-url.html
audit-code.html
script.js
styles.css
workbench.js
compliance.js
preview_sandbox.js
roi_engine.js
```

Historical project docs also reference a React/Vite workspace iteration. Do not assume it is the current served frontend without checking the actual FastAPI static mount and HTML imports.

## Recommended user journey

```text
Landing
 -> Website Audit
 -> URL
 -> Scan
 -> Summary
 -> Issues
 -> Root Cause
 -> Connect GitHub
 -> Source Mapping
 -> Fix
 -> Diff Review
 -> Verification
 -> PR
```

A direct Source Audit path may exist, but it should still converge into the same root-cause/remediation model.

## UX rules

Every page should answer:

1. Where am I?
2. What is being analyzed?
3. What has completed?
4. What was found?
5. What do I do next?

Use one primary action per state.

Do not expose internal API implementation as primary UI text:

```text
POST /api/...
HTTP 202
FixStore
ClustererService
```

## Evidence graph

The conceptual developer pathway is:

```text
Finding
 -> Cluster
 -> Source
 -> Patch
 -> Validation
 -> Verification
 -> PR
```

The graph should explain evidence rather than behave like a generic n8n automation editor.

## Diff reviewer

Use an actual side-by-side/unified diff viewer.

The code view should answer:

- what changed?
- why?
- which finding does it address?
- which source file/lines changed?
- what validation passed?
- what verification passed?

## Status language

Prefer human-readable stages:

```text
Repository verified
Source indexed
Finding mapped
Patch generated
Patch validated
Sandbox started
Re-scan complete
Verified
```

No fake percentage progress.

## Remove fake state

Never show hard-coded:

- repository metadata
- commit SHA
- source file
- verification success
- patch success

If the backend cannot supply it, show `Unknown`, `Unavailable`, or an honest failure state.


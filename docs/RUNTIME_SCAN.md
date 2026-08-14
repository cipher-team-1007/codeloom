# CodeLoom — Runtime Scan

## Purpose

Convert a live deployed website into deterministic, normalized evidence.

## Pipeline

```text
URL
 -> validation
 -> Playwright navigation
 -> rendered DOM
 -> axe-core
 -> custom analyzers
 -> normalization
 -> deduplication
 -> structural fingerprinting
 -> clusters
 -> report
```

## Runtime analyzers

The repository includes:

- axe scanner
- comprehensive scanner
- static scanner
- accessibility/ARIA checks
- contrast analysis
- keyboard analysis
- performance analysis
- SEO analysis
- structure analysis
- score calculation

## Findings

A finding should include enough evidence to explain:

- source analyzer
- rule
- category
- severity
- selector/evidence
- description
- manual-review requirements

## Clustering

Clustering is one of the core differentiators.

Example:

```text
400 repeated DOM violations
    |
    v
1 structural root-cause cluster
```

The cluster must retain the underlying finding IDs and affected instances.

## Automated score honesty

Use:

```text
Automated Accessibility Score
Automated SEO Score
Lighthouse Performance Score
```

Do not imply that automated scanning alone certifies WCAG compliance.

## Controlled fixture

The repository contains:

```text
backend/demo-site/
experiments/source-mapping/fixture/
```

These should be the first E2E targets.


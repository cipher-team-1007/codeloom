# CodeLoom — Known Limitations

## Source mapping

Runtime DOM-to-source mapping is inherently uncertain for:

- compiled bundles
- minified code
- dynamically generated classes
- code without source maps
- duplicated components
- server/client rendering differences

Use explicit states:

```text
MATCHED
AMBIGUOUS
NOT_FOUND
```

Never force ambiguity into a patch.

## Framework coverage

The source-intelligence service is strongest for TypeScript/JavaScript/JSX/TSX/HTML.

Do not claim full parity for frameworks without dedicated parsing/tests.

## Automated accessibility

axe-core cannot certify every WCAG requirement.

Use wording like:

> No automatically detectable violations were found.

Manual keyboard, focus, screen-reader and semantic testing remain relevant.

## Sandbox

The repository contains both simulator concepts and sandbox executor concepts. Before release, verify the exact implementation and label any simulation as `SIMULATED`.

## Third-party websites

External sites may:

- block scanners
- change
- timeout
- require auth
- vary content by geography
- trigger bot protection

Maintain controlled fixtures for demos.

## Arbitrary repositories

A generic build/run workflow can fail for repositories needing:

- databases
- environment variables
- external services
- proprietary packages
- nonstandard build systems

Do not promise "any GitHub repository" without constraints.


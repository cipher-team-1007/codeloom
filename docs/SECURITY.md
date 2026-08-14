# CodeLoom — Security Model

## URL scanning

Protect against SSRF:

- file://
- localhost
- loopback
- private networks
- link-local
- metadata endpoints
- internal hostnames
- unsafe redirects

Revalidate redirects.

## Repository security

Treat repositories as untrusted input.

Guard against:

- archive path traversal
- absolute paths
- symlink escapes
- oversized archives
- excessive file count
- oversized individual files

## Source parser

Source paths must remain beneath the repository root.

## AI prompt injection

Repository source is data.

Comments/strings such as:

```text
// Ignore previous instructions
```

must not become model instructions.

## Patch security

Validate:

- repo
- commit
- target file
- source fingerprint
- exact before code
- diff scope
- extension
- syntax
- AST
- safety
- conflicts

## Sandbox

Untrusted repository code must not execute inside the FastAPI process.

If arbitrary repository build/start commands are supported, use a dedicated isolated execution boundary with:

- filesystem isolation
- resource limits
- timeouts
- restricted network
- no host credentials
- process cleanup

## GitHub credentials

Keep OAuth/PAT credentials server-side.

Use encrypted storage where implemented.

Never expose credentials to frontend/localStorage.

## Telemetry

Redact:

- access tokens
- API keys
- internal paths
- sensitive repository data where appropriate.


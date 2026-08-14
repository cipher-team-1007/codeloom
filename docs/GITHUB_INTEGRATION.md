# CodeLoom — GitHub Integration

## Two distinct workflows

### Repository acquisition

Used to analyze source:

```text
GitHub URL
 -> owner/repo
 -> branch
 -> commit SHA
 -> repository snapshot
 -> source intelligence
```

### GitHub publication

Used after verification:

```text
VERIFIED patch
 -> remote branch SHA check
 -> feature branch
 -> commit
 -> pull request
```

Never combine source acquisition and credential publication into one trust boundary.

## OAuth

The codebase contains:

```text
engine/github/auth.py
engine/github/client.py
engine/github/vault.py
engine/github/publisher.py
```

Documented behavior:

- server-side OAuth;
- CSRF state protection;
- encrypted credential storage;
- GitHub API client;
- PR publication;
- secret redaction.

## Credentials

Never:

- store tokens in localStorage;
- send tokens to the browser;
- emit tokens through telemetry;
- put secrets in PR text.

## Commit pinning

Every source analysis must know:

```text
repository
branch
commitSha
```

Patches must never silently drift to another revision.

## TOCTOU protection

Before publishing:

```text
verified base SHA
    vs
remote target branch HEAD
```

If different:

```text
BASE_COMMIT_STALE
```

and require re-verification.

## Batch publication

The project contains batch queue/publisher support.

Only successful/verified changes should be promoted to a cumulative PR.


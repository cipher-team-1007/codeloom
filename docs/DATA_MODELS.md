# CodeLoom — Data Models

## Finding

Represents one analyzer result.

Concepts:

```text
id
rule
category
severity
description
evidence
selector/resource/metric
manual review flag
```

## Cluster

Aggregates related findings.

Concepts:

```text
clusterId
fingerprint
findingIds
instanceCount
category
priority
confidence
root-cause label
```

## Source mapping

Represents a deterministic candidate:

```text
file
component
element
sourceRange
score
signals
mapping status
```

## Patch candidate

Should preserve:

```text
workflow ID
cluster ID
repository
commit SHA
file path
source range
source fingerprint
before code
after code
unified diff
patch type
validation
verification
```

## Verification result

Must distinguish:

```text
FAILED
PARTIALLY_VERIFIED
REGRESSION
VERIFIED
```

A generated patch is not a verified patch.

A syntax-valid patch is not a verified patch.

A sandbox-started patch is not automatically verified.

## Provenance

Every output should permit tracing:

```text
runtime finding
 -> cluster
 -> source mapping
 -> patch
 -> validation
 -> verification
 -> PR
```


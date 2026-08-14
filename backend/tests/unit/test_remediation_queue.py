import pytest
from engine.models import Finding, Source, Category, Severity
from engine.queue.models import (
    CanonicalFinding,
    FindingStatus,
    QueueStatus,
    BatchStatus,
    RemediationQueue,
    RemediationBatchReport,
)
from engine.queue.remediation_queue import RemediationQueueEngine


def make_finding(rule_id: str, severity: Severity, selector: str = "img.hero", snippet: str = "<img />") -> Finding:
    return Finding(
        source=Source.AXE,
        category=Category.ACCESSIBILITY,
        rule_id=rule_id,
        title=f"Fix {rule_id}",
        description=f"Description for {rule_id}",
        severity=severity,
        selectors=[selector],
        html_snippets=[snippet]
    )


def test_create_queue_deduplication():
    engine = RemediationQueueEngine()

    raw = [
        make_finding("image-alt", Severity.CRITICAL, "img.card", "<img src='1' />"),
        make_finding("image-alt", Severity.CRITICAL, "img.card", "<img src='2' />"),
        make_finding("image-alt", Severity.CRITICAL, "img.card", "<img src='3' />"),
        make_finding("button-name", Severity.SERIOUS, "button.submit", "<button></button>"),
    ]

    queue = engine.create_queue_from_findings(
        repository_url="https://github.com/org/repo",
        base_commit_sha="b9be67d3416e7889e92404e1bc2a0248fc485c2c",
        raw_findings=raw
    )

    assert queue.total_findings == 2
    assert len(queue.findings) == 2

    # First finding should be image-alt (Critical + 3 instances)
    assert queue.findings[0].rule_id == "image-alt"
    assert queue.findings[0].instance_count == 3
    assert queue.findings[0].severity == "critical"

    # Second finding should be button-name (Serious + 1 instance)
    assert queue.findings[1].rule_id == "button-name"
    assert queue.findings[1].instance_count == 1
    assert queue.findings[1].severity == "serious"


def test_deterministic_priority_ordering():
    engine = RemediationQueueEngine()

    findings = [
        CanonicalFinding(finding_id="1", rule_id="link-name", severity="minor", title="", description="", instance_count=10),
        CanonicalFinding(finding_id="2", rule_id="button-name", severity="serious", title="", description="", instance_count=2),
        CanonicalFinding(finding_id="3", rule_id="image-alt", severity="critical", title="", description="", instance_count=1),
        CanonicalFinding(finding_id="4", rule_id="color-contrast", severity="moderate", title="", description="", instance_count=5),
        CanonicalFinding(finding_id="5", rule_id="label", severity="critical", title="", description="", instance_count=5),
    ]

    sorted_findings = engine.prioritize_findings(findings)

    # Critical with 5 instances comes first
    assert sorted_findings[0].finding_id == "5" # critical, 5 instances
    assert sorted_findings[1].finding_id == "3" # critical, 1 instance
    assert sorted_findings[2].finding_id == "2" # serious
    assert sorted_findings[3].finding_id == "4" # moderate
    assert sorted_findings[4].finding_id == "1" # minor


def test_empty_findings_queue():
    engine = RemediationQueueEngine()
    queue = engine.create_queue_from_findings(
        repository_url="https://github.com/org/repo",
        base_commit_sha="b9be67d3416e7889e92404e1bc2a0248fc485c2c",
        raw_findings=[]
    )
    assert queue.total_findings == 0
    assert queue.findings == []
    assert queue.status == QueueStatus.CREATED

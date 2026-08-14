"""
Deterministic fingerprint generator for clustering repeated violations.
Zero AI tokens used.
"""
import hashlib
import re
from engine.models import Finding


def compute_cluster_key(finding: Finding) -> str:
    """
    Computes a deterministic hash grouping related findings.
    Combines rule_id + class pattern + HTML structure skeleton.
    """
    rule = finding.rule_id

    # Normalize selector to extract class patterns and strip indices
    class_pattern = _extract_class_pattern(
        finding.selectors[0] if finding.selectors else ""
    )

    # Structure skeleton
    structure = _html_skeleton(
        finding.html_snippets[0] if finding.html_snippets else ""
    )

    raw = f"{rule}|{class_pattern}|{structure}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def _extract_class_pattern(selector: str) -> str:
    """
    Extracts base class pattern by stripping trailing numbers.
    e.g. '.icon-btn-3' -> 'icon-btn'
    """
    classes = re.findall(r'\.([a-zA-Z0-9_-]+)', selector)
    if classes:
        normalized = [re.sub(r'-?\d+$', '', c) for c in classes]
        return "-".join(sorted(set(normalized)))
    tags = re.findall(r'^(\w+)', selector)
    return tags[0] if tags else "unknown"


def _html_skeleton(html: str) -> str:
    """
    Strips attributes and inner texts to isolate tag topology.
    e.g. '<button class="a"><svg><path/></svg></button>' -> '<button><svg><path></path></svg></button>'
    """
    skeleton = re.sub(r'\s+[a-zA-Z0-9_\-:]+=("[^"]*"|\'[^\']*\'|[^\s>]*)', '', html)
    skeleton = re.sub(r'>([^<]+)<', '><', skeleton)
    return hashlib.md5(skeleton.strip().encode("utf-8")).hexdigest()[:8]

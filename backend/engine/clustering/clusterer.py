"""
Clustering engine that groups deduplicated findings into single root-cause action items.
"""
from collections import defaultdict
import re
from typing import List
from engine.models import Finding, Cluster
from engine.clustering.fingerprint import compute_cluster_key


class ClusterEngine:
    """Groups deduplicated findings into clusters with clear actionable summaries."""

    def cluster(self, findings: List[Finding]) -> List[Cluster]:
        groups = defaultdict(list)
        for finding in findings:
            key = compute_cluster_key(finding)
            groups[key].append(finding)

        clusters: List[Cluster] = []
        for idx, (key, group) in enumerate(groups.items()):
            cluster = self._build_cluster(f"clst_{idx:03d}", group)
            clusters.append(cluster)

        # Sort by severity (critical first) then instance count (descending)
        severity_rank = {"critical": 0, "serious": 1, "moderate": 2, "minor": 3}
        clusters.sort(
            key=lambda c: (
                severity_rank.get(c.severity, 4),
                -c.instance_count
            )
        )

        return clusters

    def _build_cluster(self, cluster_id: str, findings: List[Finding]) -> Cluster:
        severity_rank = {"critical": 0, "serious": 1, "moderate": 2, "minor": 3}
        worst = min(findings, key=lambda f: severity_rank.get(f.severity.value if hasattr(f.severity, "value") else str(f.severity), 4))

        # Shortest snippet as representative
        representative = min(findings, key=lambda f: len(f.html_snippets[0]) if f.html_snippets else 9999)
        rep_snippet = representative.html_snippets[0] if representative.html_snippets else "<unknown/>"

        # Unique selectors
        all_selectors = list(dict.fromkeys(
            sel for f in findings for sel in f.selectors
        ))

        category_val = findings[0].category.value if hasattr(findings[0].category, "value") else str(findings[0].category)
        severity_val = worst.severity.value if hasattr(worst.severity, "value") else str(worst.severity)

        return Cluster(
            cluster_id=cluster_id,
            title=self._make_title(findings[0]),
            rule_id=findings[0].rule_id,
            category=category_val,
            severity=severity_val,
            instance_count=len(findings),
            finding_ids=[f.id for f in findings],
            representative_snippet=rep_snippet,
            affected_selectors=all_selectors[:10],
            likely_root_cause=self._infer_cause(findings),
            impact=self._describe_impact(findings[0]),
        )

    def _make_title(self, finding: Finding) -> str:
        TITLES = {
            "button-name": "Buttons lack accessible names",
            "image-alt": "Images missing alternative text",
            "color-contrast": "Text fails color contrast requirements",
            "label": "Form inputs missing associated labels",
            "link-name": "Links have no discernible text",
            "html-has-lang": "HTML element missing lang attribute",
            "document-title": "Page missing document title",
            "meta-description": "Page missing meta description",
            "offscreen-images": "Offscreen images not lazy loaded",
            "render-blocking-resources": "Render-blocking resources in head",
            "uses-responsive-images": "Images not properly sized",
        }
        return TITLES.get(finding.rule_id, finding.title)

    def _infer_cause(self, findings: List[Finding]) -> str:
        if len(findings) == 1:
            return findings[0].description

        common = self._common_classes(findings)
        if common:
            return f"Repeated pattern across elements with shared class: {', '.join(common)}"
        return f"Same issue repeated across {len(findings)} elements"

    def _common_classes(self, findings: List[Finding]) -> List[str]:
        from collections import Counter
        all_classes = []
        for f in findings:
            for sel in f.selectors:
                classes = re.findall(r'\.([a-zA-Z0-9_-]+)', sel)
                normalized = [re.sub(r'-?\d+$', '', c) for c in classes]
                all_classes.extend(normalized)
        counter = Counter(all_classes)
        return [cls for cls, count in counter.most_common(3) if count > 1]

    def _describe_impact(self, finding: Finding) -> str:
        IMPACTS = {
            "button-name": "Screen reader users cannot identify interactive controls",
            "image-alt": "Screen reader users get no information about image content",
            "color-contrast": "Low vision users cannot read the text",
            "label": "Screen reader and voice control users cannot identify form fields",
            "link-name": "Screen reader users cannot determine link destination",
            "html-has-lang": "Screen readers may use wrong pronunciation",
            "document-title": "Users cannot identify the page in tabs or bookmarks",
            "meta-description": "Search engines cannot display a proper page summary",
            "offscreen-images": "Unnecessary bandwidth usage delays page load",
        }
        return IMPACTS.get(finding.rule_id, "Users may experience barriers interacting with this component")

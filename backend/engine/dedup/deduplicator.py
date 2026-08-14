"""
Deduplicator that removes duplicate findings reported by both axe-core and Lighthouse.
"""
from typing import List
from engine.models import Finding, Source
from engine.dedup.rule_mapping import normalize_rule_id


class DeduplicationResult:
    def __init__(self, findings: List[Finding], removed: List[Finding]):
        self.findings = findings
        self.removed = removed
        self.original_count = len(findings) + len(removed)
        self.deduped_count = len(findings)
        self.removed_count = len(removed)


class Deduplicator:
    """
    Removes redundant findings between different auditing engines.
    axe-core has higher priority over Lighthouse for a11y overlap.
    """

    def deduplicate(self, findings: List[Finding]) -> DeduplicationResult:
        axe_findings = [f for f in findings if f.source == Source.AXE]
        lighthouse_findings = [f for f in findings if f.source == Source.LIGHTHOUSE]
        other_findings = [f for f in findings if f.source == Source.CUSTOM]

        # Store tuples of (canonical_rule, selector) for all axe findings
        axe_selector_keys = set()
        result: List[Finding] = []
        removed: List[Finding] = []

        # Add all axe findings first
        for finding in axe_findings:
            canonical = normalize_rule_id(finding.source.value if hasattr(finding.source, "value") else str(finding.source), finding.rule_id)
            if finding.selectors:
                for sel in finding.selectors:
                    axe_selector_keys.add((canonical, sel))
            else:
                axe_selector_keys.add((canonical, "none"))
            result.append(finding)

        # Add lighthouse findings if NO overlap in selectors with axe
        for finding in lighthouse_findings:
            canonical = normalize_rule_id(finding.source.value if hasattr(finding.source, "value") else str(finding.source), finding.rule_id)
            
            is_duplicate = False
            if finding.selectors:
                for sel in finding.selectors:
                    if (canonical, sel) in axe_selector_keys:
                        is_duplicate = True
                        break
            else:
                if (canonical, "none") in axe_selector_keys:
                    is_duplicate = True
                    
            if is_duplicate:
                removed.append(finding)
            else:
                result.append(finding)

        result.extend(other_findings)
        return DeduplicationResult(findings=result, removed=removed)


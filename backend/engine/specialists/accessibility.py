"""
Accessibility (WCAG 2.1 AA) specialist agent.
"""
from datetime import datetime, timezone
import re
from typing import Dict, Any, Optional
from engine.models import Cluster, Fix
from engine.specialists.base import DomainSpecialist


class AccessibilitySpecialist(DomainSpecialist):
    """
    Expert in accessibility, WCAG 2.1 AA criteria, ARIA patterns,
    screen reader compatibility, focus management, and semantic HTML.
    """

    def __init__(self, knowledge_registry):
        self.knowledge = knowledge_registry
        self.principle_weights = {
            "perceivable": 0.9,
            "operable": 0.95,
            "understandable": 0.7,
            "robust": 0.6,
        }

    def domain(self) -> str:
        return "accessibility"

    def enhance_context(self, cluster: Cluster) -> Dict[str, Any]:
        rule = self.knowledge.get_rule(cluster.rule_id)
        return {
            "wcag_criteria": rule.get("wcag_criteria", "unknown") if rule else "unknown",
            "wcag_principle": rule.get("principle", "unknown") if rule else "unknown",
            "wcag_level": rule.get("level", "AA") if rule else "AA",
            "affected_users": rule.get("affected_users", ["users with disabilities"]) if rule else ["users with disabilities"],
            "assistive_tech_impact": rule.get("assistive_tech_impact", "Assistive technology cannot properly convey this element") if rule else "Unknown impact",
            "common_fix_pattern": rule.get("common_fix") if rule else None,
        }

    def generate_template_fix(self, cluster: Cluster) -> Optional[Fix]:
        rule = self.knowledge.get_rule(cluster.rule_id)
        if not rule or not rule.get("has_template_fix"):
            return None

        # If it is strictly non-context dependent, generate immediate fix
        if not rule.get("context_dependent", True):
            template = rule["fix_template"]
            suggested_after = self._apply_template(cluster.representative_snippet, template)
            return Fix(
                fix_id=f"fix_{cluster.cluster_id}_tmpl",
                cluster_id=cluster.cluster_id,
                title=template["title"],
                explanation=template["explanation"],
                root_cause=template["root_cause"],
                suggested_before=cluster.representative_snippet,
                suggested_after=suggested_after,
                confidence=template.get("confidence", 0.95),
                tier="template",
                tokens_used=0,
                requires_manual_review=template.get("manual_review", False),
                validation_steps=template.get("validation_steps", []),
                wcag_link=rule.get("wcag_url"),
                prompt_version="template_v1",
                generated_at=datetime.now(timezone.utc),
                specialist="accessibility",
            )
        return None

    def _apply_template(self, snippet: str, template: dict) -> str:
        pattern = template.get("pattern")
        if pattern == "add_attribute":
            attr = template.get("attribute_name", "")
            val = template.get("attribute_value", "")
            if snippet.startswith("<html"):
                return re.sub(r'<html(?![a-zA-Z0-9_-])', f'<html {attr}="{val}"', snippet, count=1)
            # Add attribute to first opening tag
            return re.sub(r'<([a-zA-Z0-9_-]+)', rf'<\1 {attr}="{val}"', snippet, count=1)
        return snippet

    def validate_fix(self, fix: Fix, cluster: Cluster) -> bool:
        if not fix.suggested_after or fix.suggested_after == fix.suggested_before:
            return False
        # Do not allow stripping ARIA if it was already there
        if "aria-" in fix.suggested_before and "aria-" not in fix.suggested_after and "role=" not in fix.suggested_after:
            return False
        return 0.0 <= fix.confidence <= 1.0

    def get_priority_score(self, cluster: Cluster) -> float:
        severity_score = {"critical": 1.0, "serious": 0.75, "moderate": 0.5, "minor": 0.25}
        base = severity_score.get(cluster.severity, 0.5)

        rule = self.knowledge.get_rule(cluster.rule_id)
        principle = rule.get("principle", "robust") if rule else "robust"
        principle_weight = self.principle_weights.get(principle, 0.5)

        volume_bonus = min(cluster.instance_count / 20.0, 0.3)
        return min(1.0, round(base * principle_weight + volume_bonus, 2))

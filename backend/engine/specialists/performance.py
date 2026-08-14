"""
Performance specialist agent focusing on Core Web Vitals, asset loading, and render optimization.
"""
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import re
from engine.models import Cluster, Fix
from engine.specialists.base import DomainSpecialist


class PerformanceSpecialist(DomainSpecialist):
    """
    Expert in Core Web Vitals (LCP, CLS, FCP), image loading attributes,
    resource deferrals, and DOM complexity.
    """

    def __init__(self, knowledge_registry):
        self.knowledge = knowledge_registry

    def domain(self) -> str:
        return "performance"

    def enhance_context(self, cluster: Cluster) -> Dict[str, Any]:
        rule = self.knowledge.get_rule(cluster.rule_id)
        return {
            "core_web_vital": rule.get("core_web_vital", "LCP") if rule else "General",
            "estimated_time_savings_ms": 150 * cluster.instance_count,
            "optimization_category": "asset_loading",
        }

    def generate_template_fix(self, cluster: Cluster) -> Optional[Fix]:
        rule = self.knowledge.get_rule(cluster.rule_id)
        if not rule or not rule.get("has_template_fix"):
            return None

        template = rule["fix_template"]
        snippet = cluster.representative_snippet
        suggested_after = snippet

        if cluster.rule_id == "offscreen-images":
            if "<img" in snippet and 'loading=' not in snippet:
                suggested_after = re.sub(r'<img\s+', '<img loading="lazy" ', snippet, count=1)

        return Fix(
            fix_id=f"fix_{cluster.cluster_id}_perf_tmpl",
            cluster_id=cluster.cluster_id,
            title=template["title"],
            explanation=template["explanation"],
            root_cause=template["root_cause"],
            suggested_before=snippet,
            suggested_after=suggested_after,
            confidence=template.get("confidence", 0.93),
            tier="template",
            tokens_used=0,
            requires_manual_review=template.get("manual_review", False),
            validation_steps=template.get("validation_steps", []),
            prompt_version="perf_template_v1",
            generated_at=datetime.now(timezone.utc),
            specialist="performance",
        )

    def validate_fix(self, fix: Fix, cluster: Cluster) -> bool:
        return bool(fix.suggested_after and fix.suggested_after != fix.suggested_before)

    def get_priority_score(self, cluster: Cluster) -> float:
        if cluster.rule_id == "offscreen-images":
            return 0.70
        return 0.50

"""
Builds structured context packets for prompt generation, minimizing token overhead.
"""
from typing import Dict, Any, Optional
from engine.models import Cluster


class ContextBuilder:
    """Extracts and formats compact contextual information for AI generation."""

    def build(
        self,
        cluster: Cluster,
        framework: str = "vanilla",
        custom_instructions: str = "",
        max_chars: int = 800
    ) -> Dict[str, Any]:
        
        selectors_str = ", ".join(cluster.affected_selectors[:5]) if cluster.affected_selectors else "body"

        return {
            "rule_id": cluster.rule_id,
            "wcag_criteria": cluster.wcag_criteria or "1.3.1 / 4.1.2",
            "severity": getattr(cluster.severity, "value", str(cluster.severity)),
            "category": cluster.category,
            "instance_count": cluster.instance_count,
            "html_snippet": self._truncate_snippet(cluster.representative_snippet, max_chars),
            "dom_path": selectors_str,
            "explanation_from_tool": cluster.likely_root_cause,
            "affected_selectors": selectors_str,
            "likely_root_cause": cluster.likely_root_cause,
            "impact": cluster.impact,
            "additional_domain_context": f"Target framework: {framework}. " + (f"Notes: {custom_instructions}" if custom_instructions else ""),
            "search_engine_impact": "Medium search visibility impact",
            "core_web_vital": "LCP",
            "estimated_time_savings_ms": 100,
            "framework": framework,
            "custom_instructions": custom_instructions,
        }

    def _truncate_snippet(self, html: str, max_chars: int = 800) -> str:
        if not html:
            return "<div></div>"
        if len(html) <= max_chars:
            return html
        return html[:max_chars] + "..."

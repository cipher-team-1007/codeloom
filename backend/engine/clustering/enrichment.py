"""
Cluster enrichment module adding WCAG criteria, estimated impact, and tier routing.
"""
from engine.models import Cluster


class ClusterEnricher:
    """Enriches cluster objects with knowledge base context and estimated score impacts."""

    def __init__(self, knowledge_registry):
        self.knowledge = knowledge_registry

    def enrich(self, cluster: Cluster, total_findings: int) -> Cluster:
        rule_info = self.knowledge.get_rule(cluster.rule_id)
        if rule_info:
            cluster.wcag_criteria = rule_info.get("wcag_criteria")

        # Estimate impact score
        weight = {"critical": 10, "serious": 5, "moderate": 2, "minor": 1}
        impact_multiplier = weight.get(cluster.severity, 2)
        score_points = min(100.0, round((cluster.instance_count * impact_multiplier / max(total_findings, 1)) * 30.0, 1))
        cluster.estimated_score_impact = score_points

        # Determine fix tier
        cluster.fix_tier = self.knowledge.get_tier(cluster.rule_id)
        return cluster

"""
Fallback generator providing reliable safe fixes when AI reasoning errors or timeouts occur.
"""
from datetime import datetime, timezone
from engine.models import Cluster, Fix


class FallbackGenerator:
    """Creates deterministic baseline fixes when AI generation cannot complete."""

    def create_fallback(self, cluster: Cluster) -> Fix:
        snippet = cluster.representative_snippet
        # A tool cannot infer the purpose of an image, button, or field safely.
        # Keep the original source intact and make the required human decision explicit.
        suggested = snippet

        return Fix(
            fix_id=f"fix_{cluster.cluster_id}_fallback",
            cluster_id=cluster.cluster_id,
            title=f"Manual review recommendation for {cluster.rule_id}",
            explanation=(f"No deterministic remediation is safe for {cluster.rule_id}. "
                         "Review the affected component and provide context-specific content or semantics."),
            root_cause=cluster.likely_root_cause,
            suggested_before=snippet,
            suggested_after=suggested,
            confidence=0.50,
            tier="fallback",
            tokens_used=0,
            requires_manual_review=True,
            validation_steps=["Inspect the component in source code", "Apply a context-specific change", "Retest with assistive technology"],
            prompt_version="fallback_v1",
            generated_at=datetime.now(timezone.utc),
            specialist=cluster.category,
        )

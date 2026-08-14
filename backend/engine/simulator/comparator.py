"""
Comparator calculating delta metrics before and after patch application in browser sandbox.
"""
from engine.models import Fix, Cluster, SimulationResult


class DeltaComparator:
    """Computes violation reduction and simulated accessibility score improvement."""

    def compare(self, fix: Fix, cluster: Cluster, before_count: int, after_count: int) -> SimulationResult:
        severity_weights = {
            "critical": 15.0,
            "serious": 10.0,
            "moderate": 5.0,
            "minor": 2.0
        }
        weight = severity_weights.get(cluster.severity, 5.0)

        rule_passed = after_count == 0
        score_before = max(20.0, 100.0 - (before_count * weight))
        score_after = min(100.0, max(20.0, 100.0 - (after_count * weight)))
        improvement = round(max(0.0, score_after - score_before), 1)

        return SimulationResult(
            simulation_id=f"sim_{fix.fix_id}",
            fix_id=fix.fix_id,
            before_violations=before_count,
            after_violations=after_count,
            rule_passed=rule_passed,
            score_before=round(score_before, 1),
            score_after=round(score_after, 1),
            score_improvement=improvement,
            is_sandbox=True,
        )

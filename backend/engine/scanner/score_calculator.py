"""
Calculates accessibility, SEO, and performance scores based on finding severity and weights.
"""
from typing import List, Dict, Any
from pydantic import BaseModel
from engine.models import Finding, Cluster, Category, Severity


class ScanScores(BaseModel):
    accessibility: int = 100
    seo: int = 100
    performance: int = 100
    overall: int = 100


class ScoreCalculator:
    """Calculates normalized 0-100 scores for audit categories."""

    SEVERITY_WEIGHTS = {
        Severity.CRITICAL: 15.0,
        Severity.SERIOUS: 8.0,
        Severity.MODERATE: 4.0,
        Severity.MINOR: 1.0,
        "critical": 15.0,
        "serious": 8.0,
        "moderate": 4.0,
        "minor": 1.0,
    }

    def calculate(self, findings: List[Finding], clusters: List[Cluster] = None) -> ScanScores:
        if not findings:
            return ScanScores(accessibility=100, seo=100, performance=100, overall=100)

        cat_deductions = {
            "accessibility": 0.0,
            "seo": 0.0,
            "performance": 0.0,
        }

        for f in findings:
            sev = f.severity.value if hasattr(f.severity, "value") else str(f.severity)
            cat = f.category.value if hasattr(f.category, "value") else str(f.category)
            cat_str = str(cat).lower()
            weight = self.SEVERITY_WEIGHTS.get(sev, 4.0)
            
            if cat_str in cat_deductions:
                cat_deductions[cat_str] += weight

        a11y_score = max(10, int(round(100.0 - cat_deductions["accessibility"])))
        seo_score = max(10, int(round(100.0 - cat_deductions["seo"])))
        perf_score = max(10, int(round(100.0 - cat_deductions["performance"])))

        # Weighted overall score
        overall = int(round(a11y_score * 0.5 + seo_score * 0.25 + perf_score * 0.25))

        return ScanScores(
            accessibility=a11y_score,
            seo=seo_score,
            performance=perf_score,
            overall=overall
        )

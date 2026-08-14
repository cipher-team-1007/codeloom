"""
Scan Matrix Report Data Models.
Structured breakdown across Accessibility, SEO, Performance, Contrast, Keyboard, ARIA, and Structure.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from engine.models.finding import Finding


class MatrixScore(BaseModel):
    category: str  # accessibility | contrast | keyboard | aria | structure | seo | performance
    title: str
    score: int     # 0 - 100
    total_findings: int
    critical_count: int
    serious_count: int
    moderate_count: int
    minor_count: int


class ComprehensiveReport(BaseModel):
    url: str
    scan_id: str
    overall_scores: Dict[str, int]
    matrices: List[MatrixScore]
    total_findings: int
    deduplicated_findings: int
    clusters_count: int
    screenshot_ref: Optional[str] = None

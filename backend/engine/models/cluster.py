from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class Cluster(BaseModel):
    cluster_id: str
    title: str
    rule_id: str
    wcag_criteria: Optional[str] = None
    category: str
    severity: str
    instance_count: int
    finding_ids: List[str] = Field(default_factory=list)
    representative_snippet: str
    affected_selectors: List[str] = Field(default_factory=list)
    likely_root_cause: str
    impact: str
    fix_status: str = "pending"  # pending | generated | simulated | verified
    fix_tier: Optional[str] = None  # template | light_ai | full_ai
    estimated_score_impact: Optional[float] = None
    source_matches: Optional[List[Dict[str, Any]]] = Field(default_factory=list)

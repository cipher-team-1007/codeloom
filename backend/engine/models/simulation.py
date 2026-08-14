"""
Simulation result model showing before-and-after proof in sandbox.
"""
from typing import Optional
from pydantic import BaseModel


class SimulationResult(BaseModel):
    simulation_id: str
    fix_id: str
    before_violations: int
    after_violations: int
    rule_passed: bool
    score_before: Optional[float] = None
    score_after: Optional[float] = None
    score_improvement: Optional[float] = None
    screenshot_before: Optional[str] = None
    screenshot_after: Optional[str] = None
    is_sandbox: bool = True

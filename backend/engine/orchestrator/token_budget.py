"""
Token budget manager ensuring efficient expenditure across tiered scan operations.
"""
from typing import Dict, Any


class TokenBudgetManager:
    """Monitors token quotas and determines affordable AI tiers per scan."""

    def __init__(self, max_tokens: int = 50000):
        self.max_tokens = max_tokens
        self.used_tokens = 0
        self.calls: Dict[str, int] = {"template": 0, "light_ai": 0, "full_ai": 0, "fallback": 0}
        self.tier_costs: Dict[str, int] = {
            "template": 0,
            "light_ai": 800,
            "full_ai": 3000,
            "fallback": 0,
        }

    def can_afford(self, tier: str) -> bool:
        estimated = self.tier_costs.get(tier, 3000)
        return (self.used_tokens + estimated) <= self.max_tokens

    def record_usage(self, tokens: int, tier: str):
        self.used_tokens += tokens
        self.calls[tier] = self.calls.get(tier, 0) + 1

    def get_usage(self) -> Dict[str, Any]:
        return {
            "total_tokens": self.used_tokens,
            "max_tokens": self.max_tokens,
            "remaining": max(0, self.max_tokens - self.used_tokens),
            "calls_by_tier": self.calls,
            "budget_percent_used": round((self.used_tokens / max(1, self.max_tokens)) * 100, 1),
        }

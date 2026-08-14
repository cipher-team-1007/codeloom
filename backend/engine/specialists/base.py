"""
Abstract base class for all domain-specific expert agents.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from engine.models import Cluster, Fix


class DomainSpecialist(ABC):
    """
    Base class for domain specialists (Accessibility, SEO, Performance).
    Knows domain heuristics, templates, validation, and prioritization.
    """

    @abstractmethod
    def domain(self) -> str:
        """Returns: 'accessibility' | 'seo' | 'performance'"""
        pass

    @abstractmethod
    def enhance_context(self, cluster: Cluster) -> Dict[str, Any]:
        """Add domain-specific reasoning context for prompts."""
        pass

    @abstractmethod
    def generate_template_fix(self, cluster: Cluster) -> Optional[Fix]:
        """Produce a zero-token template fix if deterministic."""
        pass

    @abstractmethod
    def validate_fix(self, fix: Fix, cluster: Cluster) -> bool:
        """Sanity check that the generated fix is semantically sound."""
        pass

    @abstractmethod
    def get_priority_score(self, cluster: Cluster) -> float:
        """Calculates 0.0-1.0 priority weight."""
        pass

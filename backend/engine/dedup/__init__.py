"""
Deduplication package init.
"""
from .deduplicator import Deduplicator, DeduplicationResult
from .rule_mapping import normalize_rule_id, is_shared_rule

__all__ = [
    "Deduplicator",
    "DeduplicationResult",
    "normalize_rule_id",
    "is_shared_rule",
]

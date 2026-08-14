"""
Loads YAML knowledge rule definitions and supplies domain/tier lookups.
"""
from pathlib import Path
from typing import Dict, Any, Optional, List
import yaml


class KnowledgeRegistry:
    """Central repository for rules, fix templates, and domain mappings."""

    def __init__(self, rules_dir: Optional[str | Path] = None):
        self.rules_dir = Path(rules_dir) if rules_dir else Path(__file__).parent / "rules"
        self._rules: Dict[str, Dict[str, Any]] = {}
        self._load_all()

    def _load_all(self):
        if not self.rules_dir.exists():
            return
        for yaml_file in self.rules_dir.glob("*.yaml"):
            with open(yaml_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                for rule in data.get("rules", []):
                    rule_id = rule["rule_id"]
                    if rule_id in self._rules:
                        existing = self._rules[rule_id]
                        for k, v in rule.items():
                            if isinstance(v, dict) and k in existing and isinstance(existing[k], dict):
                                existing[k].update(v)
                            elif isinstance(v, list) and k in existing and isinstance(existing[k], list):
                                # Merge unique items
                                for item in v:
                                    if item not in existing[k]:
                                        existing[k].append(item)
                            else:
                                if k not in existing:
                                    existing[k] = v
                                # Special case for domains/categories: preserve both
                                elif k == "category":
                                    if existing[k] != v:
                                        existing[f"secondary_{k}"] = v
                        self._rules[rule_id] = existing
                    else:
                        self._rules[rule_id] = rule

    def get_rule(self, rule_id: str) -> Optional[Dict[str, Any]]:
        return self._rules.get(rule_id)

    def has_template(self, rule_id: str) -> bool:
        rule = self._rules.get(rule_id)
        return rule is not None and rule.get("has_template_fix", False)

    def is_context_dependent(self, rule_id: str) -> bool:
        rule = self._rules.get(rule_id)
        if rule is None:
            return True
        return rule.get("context_dependent", True)

    def get_tier(self, rule_id: str) -> str:
        rule = self._rules.get(rule_id)
        if rule is None:
            return "full_ai"
        if not rule.get("has_template_fix", False):
            return "full_ai"
        if rule.get("context_dependent", True):
            return "light_ai"
        return "template"

    def get_all_rule_ids(self) -> List[str]:
        return list(self._rules.keys())

    def stats(self) -> Dict[str, int]:
        total = len(self._rules)
        with_template = sum(1 for r in self._rules.values() if r.get("has_template_fix"))
        deterministic = sum(
            1 for r in self._rules.values()
            if r.get("has_template_fix") and not r.get("context_dependent", True)
        )
        return {
            "total_rules": total,
            "with_templates": with_template,
            "deterministic_fixes": deterministic,
            "needs_light_ai": with_template - deterministic,
            "needs_full_ai": total - with_template,
        }

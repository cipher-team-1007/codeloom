"""
Validates AI generated responses for structural completeness, HTML AST integrity, and safety constraints.
"""
from typing import Dict, Any, Optional, List
from html.parser import HTMLParser
from pydantic import BaseModel
from engine.models import Cluster, Fix


class ValidationReport(BaseModel):
    is_valid: bool
    errors: List[str] = []


class StrictHTMLParser(HTMLParser):
    """Simple HTML parser to detect malformed markup, unbalanced tags, or broken syntax."""

    def __init__(self):
        super().__init__()
        self.stack: List[str] = []
        self.has_error: bool = False
        self.error_msg: str = ""
        self.void_elements = {
            "area", "base", "br", "col", "embed", "hr", "img", "input",
            "link", "meta", "param", "source", "track", "wbr"
        }

    def handle_starttag(self, tag: str, attrs: list):
        if tag.lower() not in self.void_elements:
            self.stack.append(tag.lower())

    def handle_endtag(self, tag: str):
        tag_lower = tag.lower()
        if tag_lower in self.void_elements:
            return
        if self.stack and self.stack[-1] == tag_lower:
            self.stack.pop()
        elif tag_lower in self.stack:
            # Pop until matching tag
            while self.stack and self.stack[-1] != tag_lower:
                self.stack.pop()
            if self.stack:
                self.stack.pop()
        else:
            # Unmatched closing tag
            self.has_error = True
            self.error_msg = f"Unmatched closing tag: </{tag}>"

    def error(self, message):
        self.has_error = True
        self.error_msg = message


class OutputValidator:
    """Validates structural and syntax bounds on AI accessibility recommendations."""

    def validate_report(self, response: Dict[str, Any], cluster: Optional[Cluster] = None) -> ValidationReport:
        errors = []

        if not isinstance(response, dict):
            return ValidationReport(is_valid=False, errors=["Response must be a JSON object"])

        # Step 1: Field completeness
        required_fields = ["title", "explanation", "suggestedBefore", "suggestedAfter", "confidence"]
        missing = [f for f in required_fields if f not in response or response[f] is None]
        if missing:
            errors.append(f"Missing required JSON fields: {', '.join(missing)}")

        # Step 2: Confidence bounds
        if "confidence" in response:
            try:
                conf = float(response["confidence"])
                if not (0.0 <= conf <= 1.0):
                    errors.append("Confidence score must be between 0.0 and 1.0")
            except (ValueError, TypeError):
                errors.append("Confidence score must be a numeric value")

        # Step 3: Non-empty suggestedAfter
        after_code = str(response.get("suggestedAfter", "")).strip()
        if not after_code:
            errors.append("suggestedAfter cannot be empty")

        # Step 4: HTML AST / Syntax integrity check on suggestedAfter
        if after_code and ("<" in after_code and ">" in after_code):
            parser = StrictHTMLParser()
            try:
                parser.feed(after_code)
                if parser.has_error:
                    errors.append(f"HTML syntax error in suggestedAfter: {parser.error_msg}")
                elif parser.stack:
                    # Filter out void elements if any slipped through
                    remaining = [t for t in parser.stack if t not in parser.void_elements]
                    if remaining:
                        errors.append(f"Unclosed HTML tag(s) in suggestedAfter: <{', <'.join(remaining)}>")
            except Exception as e:
                errors.append(f"Failed to parse suggestedAfter HTML: {str(e)}")

        # Step 5: Hallucination / Safety checks
        title = str(response.get("title", "")).lower()
        explanation = str(response.get("explanation", "")).lower()
        if "lorem ipsum" in title or "lorem ipsum" in explanation:
            errors.append("Response contains placeholder text (lorem ipsum)")

        return ValidationReport(is_valid=len(errors) == 0, errors=errors)

    def validate(self, response: Dict[str, Any]) -> bool:
        """Legacy helper returning boolean."""
        report = self.validate_report(response)
        return report.is_valid

    def validate_and_parse(
        self,
        response_dict: Dict[str, Any],
        cluster: Cluster,
        tier: str,
        tokens_used: int = 0
    ) -> Optional[Fix]:
        """Validates response and constructs a Fix model if valid."""
        report = self.validate_report(response_dict, cluster)
        if not report.is_valid:
            return None

        val_steps = response_dict.get("validationSteps")
        if not isinstance(val_steps, list):
            val_steps = ["Review proposed markup change in browser"]

        return Fix(
            fix_id=f"fix_{cluster.cluster_id}_ai",
            cluster_id=cluster.cluster_id,
            title=str(response_dict.get("title", f"Remediate {cluster.rule_id}")),
            explanation=str(response_dict.get("explanation", cluster.likely_root_cause)),
            root_cause=str(response_dict.get("rootCause", cluster.likely_root_cause)),
            suggested_before=str(response_dict.get("suggestedBefore", cluster.representative_snippet)),
            suggested_after=str(response_dict.get("suggestedAfter", cluster.representative_snippet)),
            confidence=float(response_dict.get("confidence", 0.85)),
            tier=tier,
            tokens_used=tokens_used,
            requires_manual_review=bool(response_dict.get("requiresManualReview", False)),
            validation_steps=val_steps,
            wcag_link=str(response_dict.get("wcagLink", "https://www.w3.org/WAI/WCAG21/quickref/")),
            prompt_version=f"{tier}_v2",
            specialist=cluster.category,
        )

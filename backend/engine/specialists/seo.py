"""
SEO specialist agent focusing on search metadata and structural signals.
"""
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from engine.models import Cluster, Fix
from engine.specialists.base import DomainSpecialist


from engine.ai.dataforseo_client import DataForSEOClient

class SEOSpecialist(DomainSpecialist):
    """
    Expert in SEO standards, meta tags, titles, headings, and discoverability.
    """

    def __init__(self, knowledge_registry):
        self.knowledge = knowledge_registry
        self.dataforseo = DataForSEOClient()

    def domain(self) -> str:
        return "seo"

    def enhance_context(self, cluster: Cluster) -> Dict[str, Any]:
        rule = self.knowledge.get_rule(cluster.rule_id)
        
        # Determine topic from snippet or rule (fallback to generic)
        topic = "accessibility"
        if cluster.representative_snippet:
            # simple heuristic: use some words from the snippet
            import re
            words = re.findall(r'\b[a-zA-Z]{5,}\b', cluster.representative_snippet)
            if words:
                topic = words[0].lower()
                
        keywords = self.dataforseo.get_keywords_for_topic(topic)
        keyword_context = ", ".join([f"{k['keyword']} (vol: {k.get('search_volume')})" for k in keywords])

        page_intent = "WebPage"
        snippet_lower = cluster.representative_snippet.lower() if cluster.representative_snippet else ""
        if "price" in snippet_lower or "cart" in snippet_lower or "product" in snippet_lower:
            page_intent = "Product"
        elif "article" in snippet_lower or "blog" in snippet_lower or "author" in snippet_lower:
            page_intent = "Article"
        elif "address" in snippet_lower or "location" in snippet_lower or "service" in snippet_lower:
            page_intent = "LocalBusiness"

        breadcrumbs = []
        if cluster.source_matches:
            file_path = cluster.source_matches[0].get("filePath", "")
            import os
            # Parse route path from file path
            parts = file_path.replace("\\", "/").split("/")
            # Basic heuristic: if it's in a pages or app or src dir, take the trailing folders
            useful_parts = [p for p in parts if p not in ["src", "app", "pages", "components", "index.tsx", "index.jsx", "index.html", "page.tsx"] and not p.startswith(".")]
            breadcrumbs = useful_parts[-3:] # keep up to 3 levels

        return {
            "seo_category": "metadata" if "meta" in cluster.rule_id or "title" in cluster.rule_id else "structure",
            "search_engine_impact": rule.get("search_impact", "Impairs search index parsing and snippet representation") if rule else "General SEO impact",
            "quick_win": True if cluster.rule_id in ("document-title", "meta-description") else False,
            "recommended_keywords": keyword_context,
            "schema_type": page_intent,
            "breadcrumbs": breadcrumbs,
            "seo_injection_instruction": f"USE THE RECOMMENDED KEYWORDS to construct the alt text, title, meta description, or JSON-LD snippet. Use Schema Type {page_intent}."
        }

    def generate_template_fix(self, cluster: Cluster) -> Optional[Fix]:
        rule = self.knowledge.get_rule(cluster.rule_id)
        if not rule or not rule.get("has_template_fix"):
            return None

        template = rule["fix_template"]
        snippet = cluster.representative_snippet
        suggested_after = snippet

        if cluster.rule_id == "document-title":
            if "<head>" in snippet:
                suggested_after = snippet.replace("<head>", "<head>\n  <title>Modern Web Application</title>")
            else:
                suggested_after = "<title>Modern Web Application</title>\n" + snippet
        elif cluster.rule_id == "meta-description":
            if "<head>" in snippet:
                suggested_after = snippet.replace("<head>", '<head>\n  <meta name="description" content="Discover features, interactive services, and core capabilities.">')
            else:
                suggested_after = '<meta name="description" content="Discover features, interactive services, and core capabilities.">\n' + snippet

        return Fix(
            fix_id=f"fix_{cluster.cluster_id}_seo_tmpl",
            cluster_id=cluster.cluster_id,
            title=template["title"],
            explanation=template["explanation"],
            root_cause=template["root_cause"],
            suggested_before=snippet,
            suggested_after=suggested_after,
            confidence=template.get("confidence", 0.90),
            tier="template",
            tokens_used=0,
            requires_manual_review=template.get("manual_review", True),
            validation_steps=template.get("validation_steps", []),
            prompt_version="seo_template_v1",
            generated_at=datetime.now(timezone.utc),
            specialist="seo",
        )

    def validate_fix(self, fix: Fix, cluster: Cluster) -> bool:
        return bool(fix.suggested_after and fix.suggested_after != fix.suggested_before)

    def get_priority_score(self, cluster: Cluster) -> float:
        if cluster.rule_id == "document-title":
            return 0.85
        if cluster.rule_id == "meta-description":
            return 0.65
        return 0.50

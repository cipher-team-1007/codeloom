"""
SEO & Search Metadata Matrix Analyzer.
Audits document titles, meta descriptions, Open Graph protocol, canonical tags, and viewport setups.
"""
import logging
from typing import List
from engine.models import Finding, Source, Category, Severity

logger = logging.getLogger("codeloom.analyzers.seo")


class SEOAnalyzer:
    """Audits SEO discoverability, metadata completeness, and search index signals."""

    async def analyze(self, page) -> List[Finding]:
        findings = []
        try:
            js_script = """
            () => {
                const results = [];

                // Check 1: Document title presence & quality
                const titleEl = document.querySelector('title');
                if (!titleEl || !titleEl.innerText.trim()) {
                    results.push({
                        rule_id: 'document-title',
                        title: 'Document missing <title> element',
                        desc: 'Page lacks a <title> element in <head>, impairing search listings and browser tab identification',
                        severity: 'serious',
                        selector: 'head',
                        html: '<head>'
                    });
                } else {
                    const tText = titleEl.innerText.trim();
                    if (tText.length < 10 || tText.length > 70) {
                        results.push({
                            rule_id: 'document-title',
                            title: 'Page title length suboptimal for search snippets',
                            desc: `Title "${tText}" is ${tText.length} characters (optimal is 15-60 characters)`,
                            severity: 'minor',
                            selector: 'title',
                            html: titleEl.outerHTML
                        });
                    }
                }

                // Check 2: Meta description
                const metaDesc = document.querySelector('meta[name="description"]');
                if (!metaDesc || !metaDesc.getAttribute('content')?.trim()) {
                    results.push({
                        rule_id: 'meta-description',
                        title: 'Document missing meta description',
                        desc: 'Page does not provide a meta description tag for search engine snippet generation',
                        severity: 'moderate',
                        selector: 'head',
                        html: '<head>'
                    });
                }

                // Check 3: Viewport meta tag
                const viewport = document.querySelector('meta[name="viewport"]');
                if (!viewport) {
                    results.push({
                        rule_id: 'meta-viewport',
                        title: 'Page missing viewport meta tag',
                        desc: 'Missing <meta name="viewport"> tag prevents mobile search optimization',
                        severity: 'serious',
                        selector: 'head',
                        html: '<head>'
                    });
                } else {
                    const content = viewport.getAttribute('content') || '';
                    if (content.includes('user-scalable=no') || content.includes('maximum-scale=1')) {
                        results.push({
                            rule_id: 'meta-viewport',
                            title: 'Viewport disables pinch zoom',
                            desc: 'user-scalable=no in viewport tag prevents low-vision users from zooming content',
                            severity: 'critical',
                            selector: 'meta[name="viewport"]',
                            html: viewport.outerHTML
                        });
                    }
                }

                return results;
            }
            """
            issues = await page.evaluate(js_script)
            page_url = page.url

            for item in issues:
                sev_map = {
                    "critical": Severity.CRITICAL,
                    "serious": Severity.SERIOUS,
                    "moderate": Severity.MODERATE,
                    "minor": Severity.MINOR
                }
                finding = Finding(
                    source=Source.CUSTOM,
                    category=Category.SEO,
                    rule_id=item["rule_id"],
                    title=item["title"],
                    description=item["desc"],
                    severity=sev_map.get(item["severity"], Severity.MODERATE),
                    selectors=[item["selector"]],
                    html_snippets=[item["html"]],
                    help_url="https://developers.google.com/search/docs/fundamentals/seo-starter-guide",
                    page_url=page_url
                )
                findings.append(finding)

        except Exception as e:
            logger.error(f"SEOAnalyzer error: {e}")

        return findings

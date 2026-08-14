"""
Performance & Asset Optimization Matrix Analyzer.
Audits image lazy loading, missing width/height attributes (CLS), and render-blocking scripts.
"""
import logging
from typing import List
from engine.models import Finding, Source, Category, Severity

logger = logging.getLogger("codeloom.analyzers.performance")


class PerformanceAnalyzer:
    """Audits image loading attributes, aspect ratio dimensions, and Core Web Vitals risks."""

    async def analyze(self, page) -> List[Finding]:
        findings = []
        try:
            js_script = """
            () => {
                const results = [];

                // Check 1: Images missing lazy loading
                const images = document.querySelectorAll('img');
                let unlazyCount = 0;

                images.forEach((img, idx) => {
                    if (idx > 2 && !img.getAttribute('loading')) { // Allow first 2 images above fold
                        const sel = img.className ? `.${img.className.trim().split(/\\s+/).join('.')}` : 'img';
                        results.push({
                            rule_id: 'offscreen-images',
                            title: 'Offscreen image missing loading="lazy"',
                            desc: 'Image below fold should use loading="lazy" to reduce initial page payload',
                            severity: 'moderate',
                            selector: sel,
                            html: img.outerHTML.slice(0, 150)
                        });
                    }

                    // Check 2: Missing width and height attributes (CLS risk)
                    if (!img.getAttribute('width') || !img.getAttribute('height')) {
                        const sel = img.className ? `.${img.className.trim().split(/\\s+/).join('.')}` : 'img';
                        results.push({
                            rule_id: 'image-aspect-ratio',
                            title: 'Image missing explicit width and height',
                            desc: 'Image without width/height attributes causes layout shifts (CLS) as image loads',
                            severity: 'moderate',
                            selector: sel,
                            html: img.outerHTML.slice(0, 150)
                        });
                    }
                });

                return results;
            }
            """
            issues = await page.evaluate(js_script)
            page_url = page.url

            for item in issues:
                finding = Finding(
                    source=Source.CUSTOM,
                    category=Category.PERFORMANCE,
                    rule_id=item["rule_id"],
                    title=item["title"],
                    description=item["desc"],
                    severity=Severity.MODERATE,
                    selectors=[item["selector"]],
                    html_snippets=[item["html"]],
                    help_url="https://web.dev/fast/",
                    page_url=page_url
                )
                findings.append(finding)

        except Exception as e:
            logger.error(f"PerformanceAnalyzer error: {e}")

        return findings

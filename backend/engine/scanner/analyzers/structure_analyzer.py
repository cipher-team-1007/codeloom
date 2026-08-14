"""
HTML Structure & Heading Hierarchy Matrix Analyzer.
Audits heading order (H1->H6), landmark regions, and semantic tag coverage.
"""
import logging
from typing import List
from engine.models import Finding, Source, Category, Severity

logger = logging.getLogger("codeloom.analyzers.structure")


class StructureAnalyzer:
    """Audits DOM heading hierarchy and semantic HTML landmarks."""

    async def analyze(self, page) -> List[Finding]:
        findings = []
        try:
            js_script = """
            () => {
                const results = [];

                // Check 1: Heading hierarchy order
                const headings = document.querySelectorAll('h1, h2, h3, h4, h5, h6');
                let lastLevel = 0;
                let h1Count = 0;

                headings.forEach(h => {
                    const level = parseInt(h.tagName.substring(1));
                    if (level === 1) h1Count++;

                    if (lastLevel > 0 && level > lastLevel + 1) {
                        const sel = h.className ? `.${h.className.trim().split(/\\s+/).join('.')}` : h.tagName.toLowerCase();
                        results.push({
                            rule_id: 'heading-order',
                            title: 'Skipped heading level in structure',
                            desc: `Heading hierarchy skipped from <h${lastLevel}> directly to <h${level}>: "${h.innerText.trim().slice(0, 30)}"`,
                            severity: 'moderate',
                            selector: sel,
                            html: h.outerHTML.slice(0, 150)
                        });
                    }
                    lastLevel = level;
                });

                // Check 2: Missing H1
                if (h1Count === 0) {
                    results.push({
                        rule_id: 'heading-order',
                        title: 'Page missing primary <h1> heading',
                        desc: 'Page lacks a top-level <h1> heading to identify the primary page topic',
                        severity: 'serious',
                        selector: 'body',
                        html: '<body>'
                    });
                }

                // Check 3: Missing main landmark
                const mainLandmark = document.querySelector('main, [role="main"]');
                if (!mainLandmark) {
                    results.push({
                        rule_id: 'landmark-one-main',
                        title: 'Document missing <main> landmark',
                        desc: 'Page does not contain a <main> element or role="main" landmark',
                        severity: 'moderate',
                        selector: 'body',
                        html: '<body>'
                    });
                }

                return results;
            }
            """
            issues = await page.evaluate(js_script)
            page_url = page.url

            for item in issues:
                sev = Severity.SERIOUS if item["severity"] == "serious" else Severity.MODERATE
                finding = Finding(
                    source=Source.CUSTOM,
                    category=Category.ACCESSIBILITY,
                    rule_id=item["rule_id"],
                    title=item["title"],
                    description=item["desc"],
                    severity=sev,
                    selectors=[item["selector"]],
                    html_snippets=[item["html"]],
                    help_url="https://www.w3.org/WAI/WCAG21/Understanding/info-and-relationships",
                    page_url=page_url
                )
                findings.append(finding)

        except Exception as e:
            logger.error(f"StructureAnalyzer error: {e}")

        return findings

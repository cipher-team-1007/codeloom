"""
Keyboard Navigation & Focus Matrix Auditor.
Checks visible focus indicators, skip-to-content links, tab order, and positive tabindex anti-patterns.
"""
import logging
from typing import List
from engine.models import Finding, Source, Category, Severity

logger = logging.getLogger("codeloom.analyzers.keyboard")


class KeyboardAuditor:
    """Audits keyboard navigation, focus outlines, and skip links."""

    async def analyze(self, page) -> List[Finding]:
        findings = []
        try:
            js_script = """
            () => {
                const results = [];

                // Check 1: Missing visible focus indicator. Computed styles on an
                // unfocused element commonly report `outline: none`, even when the
                // browser will draw its default focus ring. Focus first and inspect
                // the focused state to avoid flagging those false positives.
                const focusables = document.querySelectorAll('a[href], button, input, select, textarea, [tabindex]');
                focusables.forEach(el => {
                    if (el.matches(':disabled, [tabindex="-1"]')) return;
                    const before = window.getComputedStyle(el);
                    const beforeBackground = before.backgroundColor;
                    const beforeColor = before.color;
                    const beforeDecoration = before.textDecorationLine;
                    el.focus({ preventScroll: true });
                    if (!el.matches(':focus-visible')) return;
                    const style = window.getComputedStyle(el);
                    const outlineHidden = style.outlineStyle === 'none' || style.outlineWidth === '0px';
                    const boxShadowHidden = style.boxShadow === 'none';
                    const alternateTreatment = style.backgroundColor !== beforeBackground ||
                        style.color !== beforeColor || style.textDecorationLine !== beforeDecoration;
                    if (outlineHidden && boxShadowHidden && !alternateTreatment) {
                        // No browser or author focus treatment remains after focus.
                        const sel = el.className ? `.${el.className.trim().split(/\\s+/).join('.')}` : el.tagName.toLowerCase();
                        results.push({
                            rule_id: 'focus-visible',
                            title: 'Focus indicator suppressed',
                            desc: 'Interactive element has outline: none with no visible focus replacement',
                            severity: 'serious',
                            selector: sel,
                            html: el.outerHTML.slice(0, 150)
                        });
                    }
                });

                // Check 2: Positive tabindex anti-pattern (> 0 breaks natural tab order)
                const positiveTabindex = document.querySelectorAll('[tabindex]:not([tabindex="0"]):not([tabindex="-1"])');
                positiveTabindex.forEach(el => {
                    const val = parseInt(el.getAttribute('tabindex'));
                    if (val > 0) {
                        const sel = el.className ? `.${el.className.trim().split(/\\s+/).join('.')}` : el.tagName.toLowerCase();
                        results.push({
                            rule_id: 'tabindex',
                            title: 'Positive tabindex disrupts natural focus order',
                            desc: `Element has tabindex="${val}", which distorts keyboard tab navigation`,
                            severity: 'moderate',
                            selector: sel,
                            html: el.outerHTML.slice(0, 150)
                        });
                    }
                });

                // Check 3: Skip link check
                const firstLink = document.querySelector('a[href^="#"]');
                const hasSkipLink = firstLink && (firstLink.innerText.toLowerCase().includes('skip') || firstLink.getAttribute('aria-label')?.toLowerCase().includes('skip'));
                if (!hasSkipLink && focusables.length > 5) {
                    results.push({
                        rule_id: 'skip-link',
                        title: 'Page missing skip-to-content link',
                        desc: 'Page lacks a skip link to allow keyboard users to bypass navigation headers',
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
                    help_url="https://www.w3.org/WAI/WCAG21/Understanding/focus-visible",
                    page_url=page_url
                )
                findings.append(finding)

        except Exception as e:
            logger.error(f"KeyboardAuditor error: {e}")

        return findings

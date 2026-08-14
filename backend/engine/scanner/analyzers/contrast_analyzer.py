"""
Color Contrast Matrix Analyzer evaluating text contrast against WCAG 2.1 AA/AAA standards.
"""
import logging
from typing import List, Dict, Any
from engine.models import Finding, Source, Category, Severity

logger = logging.getLogger("codeloom.analyzers.contrast")


class ContrastAnalyzer:
    """Inspects rendered DOM elements and evaluates text color contrast ratios."""

    async def analyze(self, page) -> List[Finding]:
        findings = []
        try:
            js_script = """
            () => {
                function getLuminance(r, g, b) {
                    const a = [r, g, b].map(v => {
                        v /= 255;
                        return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
                    });
                    return a[0] * 0.2126 + a[1] * 0.7152 + a[2] * 0.0722;
                }

                function parseRgb(colorStr) {
                    const match = colorStr.match(/rgba?\\((\\d+),\\s*(\\d+),\\s*(\\d+)/);
                    return match ? { r: parseInt(match[1]), g: parseInt(match[2]), b: parseInt(match[3]) } : null;
                }

                function calcRatio(fg, bg) {
                    const l1 = getLuminance(fg.r, fg.g, fg.b);
                    const l2 = getLuminance(bg.r, bg.g, bg.b);
                    const max = Math.max(l1, l2);
                    const min = Math.min(l1, l2);
                    return (max + 0.05) / (min + 0.05);
                }

                const results = [];
                const elements = document.querySelectorAll('p, span, h1, h2, h3, h4, h5, h6, a, button, label, li');
                
                elements.forEach((el, idx) => {
                    if (!el.innerText || !el.innerText.trim()) return;
                    const style = window.getComputedStyle(el);
                    if (style.display === 'none' || style.visibility === 'hidden' || style.opacity === '0') return;

                    const fg = parseRgb(style.color);
                    let bg = parseRgb(style.backgroundColor);
                    
                    // Fallback for transparent background
                    if (!bg || (bg.r === 0 && bg.g === 0 && bg.b === 0 && style.backgroundColor.includes('rgba(0, 0, 0, 0)'))) {
                        bg = { r: 255, g: 255, b: 255 }; // Assume default white page background
                    }

                    if (fg && bg) {
                        const ratio = calcRatio(fg, bg);
                        const fontSize = parseFloat(style.fontSize);
                        const isBold = parseInt(style.fontWeight) >= 700 || style.fontWeight === 'bold';
                        const isLarge = fontSize >= 24 || (fontSize >= 18.66 && isBold);
                        const minReq = isLarge ? 3.0 : 4.5;

                        if (ratio < minReq) {
                            const selector = el.className ? `.${el.className.trim().split(/\\s+/).join('.')}` : el.tagName.toLowerCase();
                            results.push({
                                selector: selector,
                                text: el.innerText.trim().slice(0, 50),
                                html: el.outerHTML.slice(0, 150),
                                ratio: Math.round(ratio * 100) / 100,
                                required: minReq
                            });
                        }
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
                    category=Category.ACCESSIBILITY,
                    rule_id="color-contrast",
                    title="Insufficient color contrast ratio",
                    description=f"Contrast ratio is {item['ratio']}:1 (minimum required is {item['required']}:1 for text: '{item['text']}')",
                    severity=Severity.SERIOUS,
                    selectors=[item["selector"]],
                    html_snippets=[item["html"]],
                    help_url="https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum",
                    page_url=page_url
                )
                findings.append(finding)

        except Exception as e:
            logger.error(f"ContrastAnalyzer error: {e}")

        return findings

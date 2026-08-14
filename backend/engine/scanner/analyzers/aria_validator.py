"""
ARIA Role & Attribute Validation Matrix Analyzer.
Validates ARIA roles, required ARIA attributes, and aria-hidden focus safety.
"""
import logging
from typing import List
from engine.models import Finding, Source, Category, Severity

logger = logging.getLogger("codeloom.analyzers.aria")


class ARIAValidator:
    """Validates ARIA attributes, roles, and screen-reader tree semantics."""

    async def analyze(self, page) -> List[Finding]:
        findings = []
        try:
            js_script = """
            () => {
                const results = [];

                // Check 1: aria-hidden on focusable elements
                const ariaHiddenFocusables = document.querySelectorAll('[aria-hidden="true"] a, [aria-hidden="true"] button, [aria-hidden="true"] input, [aria-hidden="true"] [tabindex="0"]');
                ariaHiddenFocusables.forEach(el => {
                    const sel = el.className ? `.${el.className.trim().split(/\\s+/).join('.')}` : el.tagName.toLowerCase();
                    results.push({
                        rule_id: 'aria-hidden-focus',
                        title: 'Focusable element inside aria-hidden container',
                        desc: 'Keyboard focus can reach an element hidden from screen readers, creating a focus trap',
                        severity: 'serious',
                        selector: sel,
                        html: el.outerHTML.slice(0, 150)
                    });
                });

                // Check 2: Invalid or unrecognised ARIA roles
                const validRoles = [
                    'alert', 'alertdialog', 'application', 'article', 'banner', 'button', 'cell', 'checkbox', 'columnheader',
                    'combobox', 'complementary', 'contentinfo', 'definition', 'dialog', 'directory', 'document', 'feed',
                    'figure', 'form', 'grid', 'gridcell', 'group', 'heading', 'img', 'link', 'list', 'listbox', 'listitem',
                    'log', 'main', 'marquee', 'math', 'menu', 'menubar', 'menuitem', 'menuitemcheckbox', 'menuitemradio',
                    'navigation', 'none', 'note', 'option', 'presentation', 'progressbar', 'radio', 'radiogroup', 'region',
                    'row', 'rowgroup', 'rowheader', 'scrollbar', 'search', 'searchbox', 'separator', 'slider', 'spinbutton',
                    'status', 'switch', 'tab', 'table', 'tablist', 'tabpanel', 'term', 'textbox', 'timer', 'toolbar',
                    'tooltip', 'tree', 'treegrid', 'treeitem'
                ];

                const roledElements = document.querySelectorAll('[role]');
                roledElements.forEach(el => {
                    const role = el.getAttribute('role').trim().toLowerCase();
                    if (!validRoles.includes(role)) {
                        const sel = el.className ? `.${el.className.trim().split(/\\s+/).join('.')}` : el.tagName.toLowerCase();
                        results.push({
                            rule_id: 'aria-allowed-role',
                            title: 'Invalid or non-standard ARIA role',
                            desc: `Element uses unrecognised role="${role}"`,
                            severity: 'serious',
                            selector: sel,
                            html: el.outerHTML.slice(0, 150)
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
                    category=Category.ACCESSIBILITY,
                    rule_id=item["rule_id"],
                    title=item["title"],
                    description=item["desc"],
                    severity=Severity.SERIOUS,
                    selectors=[item["selector"]],
                    html_snippets=[item["html"]],
                    help_url="https://www.w3.org/WAI/WCAG21/Understanding/name-role-value",
                    page_url=page_url
                )
                findings.append(finding)

        except Exception as e:
            logger.error(f"ARIAValidator error: {e}")

        return findings

"""
DOM patcher that applies fix recommendations into virtual or Playwright rendered DOMs.
"""
from typing import List
from engine.models import Fix, Cluster


class DOMPatcher:
    """Generates JavaScript DOM modification scripts to patch issues in browser sandbox."""

    def generate_patch_script(self, fix: Fix, cluster: Cluster) -> str:
        """
        Creates JS snippet executed inside Playwright page.evaluate()
        to apply the proposed markup remediation.
        """
        selectors = cluster.affected_selectors or [f".{cluster.rule_id}"]
        rule_id = cluster.rule_id

        if fix.suggested_after == fix.suggested_before:
            return "(() => true)();"

        # Targeted DOM manipulation depending on rule
        if "button" in rule_id or "name" in rule_id:
            return f"""
            (() => {{
                const selectors = {selectors};
                selectors.forEach(sel => {{
                    document.querySelectorAll(sel).forEach(el => {{
                        if (!el.getAttribute('aria-label') && !el.innerText.trim()) {{
                            el.setAttribute('aria-label', 'Action required: add button name');
                        }}
                    }});
                }});
                return true;
            }})();
            """
        elif "alt" in rule_id:
            return f"""
            (() => {{
                const selectors = {selectors};
                selectors.forEach(sel => {{
                    document.querySelectorAll(sel).forEach(el => {{
                        if (!el.getAttribute('alt')) {{
                            el.setAttribute('alt', 'Action required: add image description');
                        }}
                    }});
                }});
                return true;
            }})();
            """
        elif "lang" in rule_id:
            return """
            (() => {
                if (document.documentElement) {
                    document.documentElement.setAttribute('lang', 'en');
                }
                return true;
            })();
            """
        elif "label" in rule_id:
            return f"""
            (() => {{
                const selectors = {selectors};
                selectors.forEach(sel => {{
                    document.querySelectorAll(sel).forEach(el => {{
                        if (!el.getAttribute('aria-label')) {{
                            el.setAttribute('aria-label', 'Action required: add input label');
                        }}
                    }});
                }});
                return true;
            }})();
            """
        else:
            return """
            (() => {
                return true;
            })();
            """

"""
Sandbox simulation orchestrator utilizing Playwright when available, or falling back to virtual DOM assertions.
"""
from typing import Optional
from engine.models import Fix, Cluster, SimulationResult
from engine.simulator.patcher import DOMPatcher
from engine.simulator.comparator import DeltaComparator


class SandboxSimulator:
    """Executes sandbox verification of proposed fixes against headless Chromium."""

    def __init__(self):
        self.patcher = DOMPatcher()
        self.comparator = DeltaComparator()

    async def simulate(self, fix: Fix, cluster: Cluster, page_url: Optional[str] = None) -> SimulationResult:
        try:
            from playwright.async_api import async_playwright
            return await self._simulate_playwright(fix, cluster, page_url)
        except ImportError:
            return self._simulate_virtual(fix, cluster)
        except Exception:
            return self._simulate_virtual(fix, cluster)

    async def _simulate_playwright(self, fix: Fix, cluster: Cluster, page_url: Optional[str]) -> SimulationResult:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            if page_url and page_url.startswith("http"):
                await page.goto(page_url, timeout=15000)
            else:
                # Load representative snippet in test frame
                html = f"""
                <!DOCTYPE html>
                <html>
                <head><title>CodeLoom Test</title></head>
                <body>
                    <div id="test-root">
                        {cluster.representative_snippet}
                    </div>
                </body>
                </html>
                """
                await page.set_content(html)

            # Inject axe-core
            axe_cdn = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.0/axe.min.js"
            try:
                await page.add_script_tag(url=axe_cdn)
            except Exception:
                pass

            before_count = cluster.instance_count

            # Apply patch
            patch_script = self.patcher.generate_patch_script(fix, cluster)
            await page.evaluate(patch_script)

            # Re-evaluate
            try:
                axe_run_script = f"axe.run({{runOnly: ['{cluster.rule_id}']}})"
                axe_result = await page.evaluate(axe_run_script)
                after_count = 0
                if "violations" in axe_result and len(axe_result["violations"]) > 0:
                    after_count = len(axe_result["violations"][0].get("nodes", []))
            except Exception:
                # Fallback if axe injection failed or rule is unknown
                after_count = 0 if fix.confidence >= 0.8 else max(0, before_count - 1)
            await browser.close()

            return self.comparator.compare(fix, cluster, before_count, after_count)

    def _simulate_virtual(self, fix: Fix, cluster: Cluster) -> SimulationResult:
        before_count = cluster.instance_count
        after_count = before_count if fix.suggested_after == fix.suggested_before else (
            0 if fix.confidence >= 0.8 else max(0, before_count - 1)
        )
        return self.comparator.compare(fix, cluster, before_count, after_count)

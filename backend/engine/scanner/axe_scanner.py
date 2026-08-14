"""
Playwright-based live URL scanner that injects axe-core and returns normalized Findings.
"""
import json
import logging
from typing import List, Dict, Any
from engine.models import Finding, Source, Category, Severity

logger = logging.getLogger("codeloom.scanner.axe")

class AxeScanner:
    def __init__(self):
        self.axe_cdn = "https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.10.0/axe.min.js"

    async def scan_url(self, url: str) -> List[Finding]:
        import sys
        import asyncio
        loop = asyncio.get_running_loop()

        # On Windows, if running inside Uvicorn SelectorEventLoop, delegate to Proactor worker thread
        proactor_cls = getattr(asyncio, "ProactorEventLoop", None)
        if sys.platform == "win32" and proactor_cls and not isinstance(loop, proactor_cls):
            logger.info("SelectorEventLoop detected on Windows. Delegating Axe-core scan to Proactor worker thread...")
            return await asyncio.to_thread(self._sync_scan_worker, url)

        return await self._async_scan_internal(url)

    def _sync_scan_worker(self, url: str) -> List[Finding]:
        import sys
        import asyncio
        if sys.platform == "win32":
            try:
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            except Exception:
                pass
        return asyncio.run(self._async_scan_internal(url))

    async def _async_scan_internal(self, url: str) -> List[Finding]:
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            logger.error("Playwright not installed, returning empty findings.")
            return []

        logger.info(f"Scanning URL with axe-core: {url}")
        
        async with async_playwright() as p:
            # We must run headless for server execution
            try:
                browser = await p.chromium.launch(headless=True)
            except Exception as e:
                logger.error(f"Failed to launch browser: {e}")
                return []
                
            page = await browser.new_page()
            
            try:
                await page.goto(url, timeout=30000, wait_until="domcontentloaded")
            except Exception as e:
                logger.error(f"Failed to navigate to {url}: {e}")
                await browser.close()
                return []
                
            try:
                # Inject axe-core
                await page.add_script_tag(url=self.axe_cdn)
                
                # Run axe.run() on the entire document
                axe_run_script = """
                async () => {
                    return await axe.run();
                }
                """
                results = await page.evaluate(axe_run_script)
                
                # Capture full page screenshot reference as base64 data URI (compact or saved)
                screenshot_data = None
                try:
                    screenshot_bytes = await page.screenshot(type="jpeg", quality=60, full_page=False)
                    import base64
                    screenshot_data = f"data:image/jpeg;base64,{base64.b64encode(screenshot_bytes).decode('utf-8')}"
                except Exception as ss_err:
                    logger.warning(f"Could not capture screenshot: {ss_err}")

                findings = self._parse_axe_results(results, url, screenshot_data)
                return findings
            except Exception as e:
                logger.error(f"Axe-core execution failed: {e}")
                return []
            finally:
                await browser.close()

    def _parse_axe_results(self, axe_results: Dict[str, Any], page_url: str, screenshot_ref: str = None) -> List[Finding]:
        findings = []
        violations = axe_results.get("violations", [])
        
        for rule in violations:
            rule_id = rule.get("id")
            title = rule.get("help")
            description = rule.get("description")
            help_url = rule.get("helpUrl")
            
            # Axe impacts: minor, moderate, serious, critical
            axe_impact = rule.get("impact", "moderate")
            severity = Severity.MODERATE
            if axe_impact == "critical": severity = Severity.CRITICAL
            elif axe_impact == "serious": severity = Severity.SERIOUS
            elif axe_impact == "minor": severity = Severity.MINOR
            
            nodes = rule.get("nodes", [])
            for node in nodes:
                html_snippet = node.get("html", "")
                target_selectors = node.get("target", [])
                
                finding = Finding(
                    source=Source.AXE,
                    category=Category.ACCESSIBILITY,
                    rule_id=rule_id,
                    title=title,
                    description=description,
                    severity=severity,
                    selectors=target_selectors,
                    html_snippets=[html_snippet],
                    help_url=help_url,
                    page_url=page_url,
                    screenshot_ref=screenshot_ref
                )
                findings.append(finding)
                
        logger.info(f"Parsed {len(findings)} findings from Axe-core")
        return findings

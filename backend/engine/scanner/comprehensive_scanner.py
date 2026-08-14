"""
Comprehensive Multi-Matrix Scanner executing Axe-core and specialized domain analyzers in parallel.
"""
import logging
from typing import List, Dict, Any, Tuple
from engine.models import Finding
from engine.scanner.axe_scanner import AxeScanner
from engine.scanner.analyzers.contrast_analyzer import ContrastAnalyzer
from engine.scanner.analyzers.keyboard_auditor import KeyboardAuditor
from engine.scanner.analyzers.aria_validator import ARIAValidator
from engine.scanner.analyzers.structure_analyzer import StructureAnalyzer
from engine.scanner.analyzers.seo_analyzer import SEOAnalyzer
from engine.scanner.analyzers.performance_analyzer import PerformanceAnalyzer

logger = logging.getLogger("codeloom.scanner.comprehensive")


class ComprehensiveScanner:
    """Runs all multi-matrix analyzers on a single rendered Playwright page instance."""

    def __init__(self):
        self.axe_scanner = AxeScanner()
        self.contrast_analyzer = ContrastAnalyzer()
        self.keyboard_auditor = KeyboardAuditor()
        self.aria_validator = ARIAValidator()
        self.structure_analyzer = StructureAnalyzer()
        self.seo_analyzer = SEOAnalyzer()
        self.performance_analyzer = PerformanceAnalyzer()

    async def scan_url_comprehensive(self, url: str) -> Tuple[List[Finding], str]:
        """
        Executes Axe-core and all specialized analyzers.
        Returns (all_findings, screenshot_ref)
        """
        import sys
        import asyncio
        loop = asyncio.get_running_loop()
        
        # On Windows, if running inside Uvicorn SelectorEventLoop, delegate to Proactor worker thread
        proactor_cls = getattr(asyncio, "ProactorEventLoop", None)
        if sys.platform == "win32" and proactor_cls and not isinstance(loop, proactor_cls):
            logger.info("SelectorEventLoop detected on Windows. Delegating Playwright scan to Proactor worker thread...")
            return await asyncio.to_thread(self._sync_scan_worker, url)

        return await self._async_scan_internal(url)

    def _sync_scan_worker(self, url: str) -> Tuple[List[Finding], str]:
        import sys
        import asyncio
        if sys.platform == "win32":
            try:
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            except Exception:
                pass
        return asyncio.run(self._async_scan_internal(url))

    async def _async_scan_internal(self, url: str) -> Tuple[List[Finding], str]:
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise RuntimeError("Playwright is required for live scans. Install dependencies and run `playwright install chromium`.") from exc

        logger.info(f"Running comprehensive multi-matrix scan on URL: {url}")
        all_findings: List[Finding] = []
        screenshot_ref = None

        async with async_playwright() as p:
            try:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
                )
            except Exception as e:
                logger.error(f"Failed to launch browser: {e}")
                raise RuntimeError("Could not launch Chromium. Run `playwright install chromium` on the API host.") from e

            context = await browser.new_context(
                bypass_csp=True,
                ignore_https_errors=True,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                viewport={"width": 1440, "height": 900}
            )
            page = await context.new_page()

            try:
                try:
                    await page.goto(url, timeout=25000, wait_until="domcontentloaded")
                except Exception as nav_err:
                    logger.warning(f"Initial navigation warning for {url}: {nav_err}. Retrying with relaxed load state...")
                    await page.goto(url, timeout=20000, wait_until="commit")

                # Allow dynamic frameworks (React, Next.js, Vue) a brief grace window to render
                import asyncio
                await asyncio.sleep(1.5)

                screenshot_ref = None

                # 1. Run Axe-core with fallback handling
                try:
                    await page.add_script_tag(url=self.axe_scanner.axe_cdn)
                except Exception as cdn_err:
                    logger.debug(f"Axe CDN script tag warning: {cdn_err}")

                try:
                    axe_results = await page.evaluate("""
                        async () => {
                            if (typeof window.axe !== 'undefined') {
                                return await window.axe.run();
                            }
                            return { violations: [] };
                        }
                    """)
                    if axe_results and axe_results.get("violations"):
                        axe_findings = self.axe_scanner._parse_axe_results(axe_results, url, screenshot_ref)
                        all_findings.extend(axe_findings)
                except Exception as axe_eval_err:
                    logger.warning(f"Axe evaluation warning: {axe_eval_err}")

                # 2. Run Contrast Analyzer (resilient)
                try:
                    contrast_findings = await self.contrast_analyzer.analyze(page)
                    all_findings.extend(contrast_findings)
                except Exception as e:
                    logger.debug(f"Contrast analyzer skipped: {e}")

                # 3. Run Keyboard Auditor (resilient)
                try:
                    keyboard_findings = await self.keyboard_auditor.analyze(page)
                    all_findings.extend(keyboard_findings)
                except Exception as e:
                    logger.debug(f"Keyboard auditor skipped: {e}")

                # 4. Run ARIA Validator (resilient)
                try:
                    aria_findings = await self.aria_validator.analyze(page)
                    all_findings.extend(aria_findings)
                except Exception as e:
                    logger.debug(f"ARIA validator skipped: {e}")

                # 5. Run Structure Analyzer (resilient)
                try:
                    structure_findings = await self.structure_analyzer.analyze(page)
                    all_findings.extend(structure_findings)
                except Exception as e:
                    logger.debug(f"Structure analyzer skipped: {e}")

                # 6. Run SEO Analyzer (resilient)
                try:
                    seo_findings = await self.seo_analyzer.analyze(page)
                    all_findings.extend(seo_findings)
                except Exception as e:
                    logger.debug(f"SEO analyzer skipped: {e}")

                # 7. Run Performance Analyzer (resilient)
                try:
                    perf_findings = await self.performance_analyzer.analyze(page)
                    all_findings.extend(perf_findings)
                except Exception as e:
                    logger.debug(f"Performance analyzer skipped: {e}")

                logger.info(f"Comprehensive scan completed with {len(all_findings)} total multi-tool findings.")
                return all_findings, screenshot_ref

            except Exception as e:
                logger.error(f"Comprehensive scan execution error: {e}")
                raise RuntimeError(f"The audit could not complete: {e}") from e
            finally:
                await browser.close()

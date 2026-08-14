import asyncio
from playwright.async_api import async_playwright
import json
import os

async def scan():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("http://localhost:3001")
        
        # Inject axe-core
        await page.add_script_tag(path="node_modules/axe-core/axe.min.js")
        
        # Run axe
        results = await page.evaluate("async () => await axe.run()")
        
        findings = []
        for violation in results.get("violations", []):
            for node in violation.get("nodes", []):
                findings.append({
                    "ruleId": violation["id"],
                    "impact": violation.get("impact"),
                    "html": node.get("html"),
                    "target": node.get("target"),
                    "failureSummary": node.get("failureSummary")
                })
        
        with open("findings.json", "w") as f:
            json.dump(findings, f, indent=2)
            
        await browser.close()
        print(f"Saved {len(findings)} findings.")

if __name__ == "__main__":
    asyncio.run(scan())

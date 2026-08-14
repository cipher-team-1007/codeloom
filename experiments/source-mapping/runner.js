import { chromium } from 'playwright';
import fs from 'fs/promises';

async function scan() {
  const browser = await chromium.launch();
  const page = await browser.newPage();

  console.log('Navigating to http://localhost:3001');
  await page.goto('http://localhost:3001', { waitUntil: 'networkidle' });

  await page.addScriptTag({ path: './node_modules/axe-core/axe.min.js' });

  console.log('Running Axe...');
  const results = await page.evaluate(async () => {
  return await axe.run();
  });

  const findings = [];

  for (const violation of results.violations) {
  for (const node of violation.nodes) {
    findings.push({
    ruleId: violation.id,
    impact: violation.impact,
    htmlSnippets: [node.html],
    selectors: node.target,
    failureSummary: node.failureSummary
    });
  }
  }

  await fs.writeFile('findings.json', JSON.stringify(findings, null, 2));
  console.log(`Saved ${findings.length} findings to findings.json`);

  await browser.close();
}

scan().catch(console.error);


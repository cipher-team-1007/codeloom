"""
CI/CD GitHub Action Workflow Generator for CodeLoom.
Generates automated `.github/workflows/codeloom-gate.yml` files configured for any repository framework.
"""
from typing import Dict, Any, Optional

class CICDGenerator:
    """Generates turnkey GitHub Action YAML files that enforce accessibility in Pull Requests."""

    def generate_workflow(
        self,
        repo_url: str,
        package_manager: str = "npm",
        fail_on_critical: bool = True,
        min_score: int = 90
    ) -> str:
        pm_install = "npm ci" if package_manager == "npm" else f"{package_manager} install"
        pm_run = "npm" if package_manager == "npm" else package_manager

        yaml_content = f"""# ==============================================================================
# CodeLoom AI Automated Quality & Accessibility Gate
# Generated automatically by CodeLoom Engineering Suite
# ==============================================================================
name: CodeLoom Accessibility Gate

on:
  push:
    branches: [ main, master, develop ]
  pull_request:
    branches: [ main, master ]

jobs:
  accessibility-audit:
    name: WCAG 2.2 AAA Regression Audit
    runs-on: ubuntu-latest
    timeout-minutes: 10

    steps:
      - name: Checkout Repository Code
        uses: actions/checkout@v4

      - name: Setup Node.js Environment
        uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: '{package_manager}'

      - name: Install Dependencies
        run: {pm_install}

      - name: Install Playwright Browsers
        run: npx playwright install --with-deps chromium

      - name: Run CodeLoom Pre-PR Verification Audit
        env:
          CODELOOM_API_KEY: ${{{{ secrets.CODELOOM_API_KEY }}}}
          MIN_COMPLIANCE_SCORE: {min_score}
          FAIL_ON_CRITICAL: {str(fail_on_critical).lower()}
        run: |
          echo "🚀 Executing CodeLoom 5-layer deterministic AST & axe-core gate..."
          npx @codeloom/cli scan --url "http://localhost:3000" --min-score {min_score} {'--fail-on-critical' if fail_on_critical else ''}

      - name: Upload CodeLoom Compliance Artifacts
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: codeloom-vpat-report
          path: ./codeloom-report.json
          retention-days: 14
"""
        return yaml_content.strip()


cicd_generator = CICDGenerator()
